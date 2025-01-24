# SPDX-FileCopyrightText: 2025 Jutta-Proto
# SPDX-FileCopyrightText: 2025 Stefan Hackenberg
#
# SPDX-License-Identifier: GPL-3.0-only

import asyncio
import itertools
import logging
from dataclasses import dataclass
from types import TracebackType
from typing import Literal, Optional, Self, Type

from bleak import BleakClient, BleakScanner

from .classes import CoffeeProduct, MachineData
from .encoding import encode_decode
from .machine import Machine


@dataclass
class Characteristic:
    uuid: str
    encoded: Optional[bool]


characteristics = {
    "About Machine": Characteristic("5A401531-AB2E-2548-C435-08C300000710", False),
    "Machine Status": Characteristic("5a401524-ab2e-2548-c435-08c300000710", True),
    "Barista Mode": Characteristic("5a401530-ab2e-2548-c435-08c300000710", True),
    "Product Progress": Characteristic("5a401527-ab2e-2548-c435-08c300000710", True),
    "P Mode": Characteristic("5a401529-ab2e-2548-c435-08c300000710", True),
    "P Mode Read": Characteristic("5a401538-ab2e-2548-c435-08c300000710", None),
    "Start Product": Characteristic("5a401525-ab2e-2548-c435-08c300000710", True),
    "Statistics Command": Characteristic("5A401533-ab2e-2548-c435-08c300000710", True),
    "Statistics Data": Characteristic("5A401534-ab2e-2548-c435-08c300000710", None),
    "Update Product Statistics": Characteristic(
        "5a401528-ab2e-2548-c435-08c300000710", None
    ),
    "UART TX": Characteristic("5a401624-ab2e-2548-c435-08c300000710", True),
    "UART RX": Characteristic("5a401625-ab2e-2548-c435-08c300000710", True),
}
"""Characteristics of JURA Bluetooth Protocol."""


async def _get_key(address):
    device = await BleakScanner.find_device_by_address(address)
    manufacturer_data = list(device.details["props"]["ManufacturerData"].values())[0]
    data = MachineData.from_bytes(manufacturer_data)
    return data.key


class JuraBle:
    @staticmethod
    async def create(model: str, address: Optional[str] = None, timeout: int = 20):
        if address is None:
            devices = await BleakScanner.discover()
            for device in devices:
                if "BlueFrog" in device.name:
                    address = device.address
                    break
        if address is None:
            raise Exception("No JURA BLE device found")
        return JuraBle(
            model=model,
            address=address,
            key=await _get_key(address),
            timeout=timeout,
        )

    def __init__(self, model: str, address: str, key: int, *, timeout: int = 20):
        self.model = Machine(model)
        self.client = BleakClient(address, timeout=timeout)
        self.key = key
        self._heartbeat_task = None

    async def _read(self, characteristic: str, *, encoded: bool = True):
        result = await self.client.read_gatt_char(characteristics[characteristic].uuid)
        result = encode_decode(result, key=self.key) if encoded else result
        logging.getLogger(__name__).debug(
            f"Read from {characteristic}: '{result.hex()}'"
        )
        return result

    async def _write(
        self,
        characteristic: str,
        data: bytes,
        encoded: bool = True,
        prepend_key: bool = True,
    ):
        data = bytes([self.key]) + data if prepend_key else data
        data = encode_decode(data, key=self.key) if encoded else data
        logging.getLogger(__name__).debug(
            f"Writing to {characteristic}: '{data.hex()}'"
        )
        await self.client.write_gatt_char(characteristics[characteristic].uuid, data)

    async def about_machine(self):
        return MachineData.from_bytes(await self._read("About Machine", encoded=False))

    async def machine_status(self) -> list[str]:
        status = await self._read("Machine Status")
        status = itertools.chain(*[list(f"{x:08b}") for x in status[1:9]])
        return self.model.decode_status(status)

    async def heartbeat(self):
        logging.getLogger(__name__).debug("heartbeat")
        await self._write("P Mode", b"\x7f\x80")

    async def lock_machine(self):
        logging.getLogger(__name__).debug("lock_machine")
        await self._write("Barista Mode", b"\x01")

    async def unlock_machine(self):
        logging.getLogger(__name__).debug("unlock_machine")
        await self._write("Barista Mode", b"\x00")

    async def statistics(
        self,
        mode: Literal["total"] | Literal["daily"] = "total",
    ) -> list[int]:
        await self._write(
            "Statistics Command",
            (b"\x00\x01" if mode == "total" else b"\x00\x10") + b"\xff\xff",
        )
        await asyncio.sleep(2)
        result = await self._read("Statistics Command")
        if result[0] == 0x0E:
            raise Exception("Statistics not available")
        result = await self._read("Statistics Data")
        return [
            int.from_bytes(result[3 * i : 3 * i + 3], "big")
            for i in range(len(result) // 3)
        ]

    async def brew_product(
        self,
        product: CoffeeProduct,
    ):
        logging.getLogger(__name__).debug(f"brew_product: {product}")
        await self._write(
            "Start Product",
            product.to_bytes() + bytes([self.key]),
        )

    async def product_progress(self) -> dict[str, bytes | int] | None:
        """Returns the progress of the current product or None if machine idle."""
        status = await self._read("Product Progress")
        logging.getLogger(__name__).debug(f"product_progress: {status}")
        if status[15] == 1:
            return None
        # TODO: More reverse engineering needed
        return {"step": status[1], "product": status[2], "rest": status[3:15]}

    async def _heartbeat_periodic(self):
        while True:
            await self.heartbeat()
            await asyncio.sleep(10)

    async def __aenter__(self) -> Self:
        await self.client.connect()
        logging.getLogger(__name__).debug("Connected")
        loop = asyncio.get_event_loop()
        self._heartbeat_task = loop.create_task(self._heartbeat_periodic())
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self._heartbeat_task.cancel()
        await self.client.disconnect()
        logging.getLogger(__name__).debug("Disconnected")
