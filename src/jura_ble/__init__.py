# SPDX-FileCopyrightText: 2025 Jutta-Proto
# SPDX-FileCopyrightText: 2025 Stefan Hackenberg
#
# SPDX-License-Identifier: GPL-3.0-only

import asyncio
import itertools
import logging
from dataclasses import dataclass
from enum import Enum
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
        status = [
            int(x) for x in itertools.chain(*[list(f"{x:08b}") for x in status[1:9]])
        ]
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

    async def product_progress(self) -> "ProductProgress":
        """Returns the progress of the current product or None if machine idle."""
        progress = ProductProgress(await self._read("Product Progress"))
        logging.getLogger(__name__).debug(f"product_progress: {progress}")
        return progress

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


class ProductProgressState(Enum):
    """
    State of product progress

    Reverse engineered from
    joe_android_connector.src.connection.common.Progress$Companion$mapStateToProductProgressState$1
    """

    SMART_ALERT_PAUSE = 0x19
    MILK_FOAM_BEAN_AMOUNT = 0x31
    MILK_FOAM_MILK_VOLUME = 0x32
    MILK_FOAM_PAUSE = 0x33
    MILK_FOAM_VOLUME = 0x34
    MILK_FOAM_WATER_VOLUME = 0x37
    COFFEE_BEAN_AMOUNT = 0x39
    COFFEE_WATER_AMOUNT = 0x3C
    LAST_PROGRESS_STATE = 0x3E
    HOTWATER_TEMPERATURE = 0x40
    HOTWATER_VOLUME = 0x41
    STEAM_TEMPERATURE = 0x43


class ProductProgressArgument(Enum):
    """
    Product arguments

    Reverse engineered from
    joe_android_connector.src.connection.enums.ProductArgument
    """

    ACTUAL_COFFEE_STRENGTH = 0
    MAX_COFFEE_STRENGTH = 1
    ACTUAL_WATER_VOLUME = 2
    MAX_WATER_VOLUME = 3
    ACTUAL_MILK_TIME = 4
    MAX_MILK_TIME = 5
    ACTUAL_MILK_FOAM_TIME_STEAM_TEMPERATURE_BYPASS_WATER_AMOUNT = 6
    MAX_MILK_FOAM_TIME_STEAM_TEMPERATURE_BYPASS_WATER_AMOUNT = 7
    MAX_WATER_TEMPERATURE = 8
    ACTUAL_PAUSE_TIME = 9
    MAX_PAUSE_TIME = 10
    INTAKE_PERCENTAGE = 11
    MILK_FOAM_TEMPERATURE = 12
    INVALID = 13


class ProductProgress:
    ARGUMENT_OFFSET = 2

    def __init__(self, data: bytes) -> None:
        self._data = data[1:]

    @property
    def product_code(self) -> int:
        return self._data[1]

    @property
    def state(self) -> ProductProgressState:
        return ProductProgressState(self._data[0])

    def _arg(self, arg: ProductProgressArgument):
        return self._data[self.ARGUMENT_OFFSET + arg.value]

    @property
    def coffee_strength(self) -> tuple[int, int]:
        return (
            self._arg(ProductProgressArgument.ACTUAL_COFFEE_STRENGTH),
            self._arg(ProductProgressArgument.MAX_COFFEE_STRENGTH),
        )

    @property
    def water_volume(self) -> tuple[int, int]:
        return (
            self._arg(ProductProgressArgument.ACTUAL_WATER_VOLUME),
            self._arg(ProductProgressArgument.MAX_WATER_VOLUME),
        )

    @property
    def milk_time(self) -> tuple[int, int]:
        return (
            self._arg(ProductProgressArgument.ACTUAL_MILK_TIME),
            self._arg(ProductProgressArgument.MAX_MILK_TIME),
        )

    @property
    def milk_foam(self) -> tuple[int, int]:
        return (
            self._arg(
                ProductProgressArgument.ACTUAL_MILK_FOAM_TIME_STEAM_TEMPERATURE_BYPASS_WATER_AMOUNT
            ),
            self._arg(
                ProductProgressArgument.MAX_MILK_FOAM_TIME_STEAM_TEMPERATURE_BYPASS_WATER_AMOUNT
            ),
        )

    @property
    def water_temperature(self) -> int:
        return self._arg(ProductProgressArgument.MAX_WATER_TEMPERATURE)

    @property
    def pause_time(self) -> int:
        return self._arg(ProductProgressArgument.MAX_PAUSE_TIME)

    @property
    def intake_percentage(self) -> int:
        return self._arg(ProductProgressArgument.INTAKE_PERCENTAGE)

    @property
    def valid(self) -> bool:
        return self._arg(ProductProgressArgument.INVALID) == 0

    def __str__(self) -> str:
        return (
            "<ProductProgress "
            + " ".join(
                f"{arg}={getattr(self, arg)}"
                for arg, prop in ProductProgress.__dict__.items()
                if isinstance(prop, property)
            )
            + ">"
        )
