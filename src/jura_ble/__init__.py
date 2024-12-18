import asyncio
from dataclasses import dataclass
from typing import Optional

from bleak import BleakClient, BleakScanner

from .encoding import encode_decode
from .classes import MachineData


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
    async def create(address: str, timeout: int = 20):
        return JuraBle(address=address, key=await _get_key(address), timeout=timeout)

    def __init__(self, address: str, key: int, *, timeout: int = 20):
        self.client = BleakClient(address, timeout=timeout)
        self.key = key

    async def connect(self):
        asyncio.run(self.client.connect())

    async def _read(self, characteristic: str, encoded: bool = True):
        result = await self.client.read_gatt_char(characteristics[characteristic].uuid)
        return encode_decode(result, key=self.key) if encoded else result

    async def _write(self, characteristic: str, data: bytes, encoded: bool = True):
        await self.client.write_gatt_char(
            characteristics[characteristic].uuid,
            encode_decode(data, key=self.key) if encoded else data,
        )

    async def about_machine(self):
        return MachineData.from_bytes(await self._read("About Machine", encoded=False))

    async def machine_status(self):
        return await self._read("Machine Status")

    async def heartbeat(self):
        await self._write("P Mode", bytes([self.key]) + b"\x7f\x80")

    async def lock_machine(self):
        await self._write("Barista Mode", b"\x00\x01")

    async def unlock_machine(self):
        await self._write("Barista Mode", b"\x00\x00")

    async def statistics(self):
        await self._write("Barista Mode", b"\x00\x00")
