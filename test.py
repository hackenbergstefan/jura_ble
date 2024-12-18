import asyncio
from bleak import BleakClient

from src.jura_ble import JuraBle

address = "DB:4E:54:44:39:9F"


async def main(address):
    jura = await JuraBle.create(address)
    async with jura.client:
        print(await jura.heartbeat())
        print(await jura.about_machine())


asyncio.run(main(address))
