# SPDX-FileCopyrightText: 2025 Stefan Hackenberg
#
# SPDX-License-Identifier: CC0-1.0

import asyncio
import logging

from src.jura_ble import JuraBle

address = "DB:4E:54:44:39:9F"

logging.basicConfig(level=logging.INFO)
logging.getLogger("src.jura_ble").setLevel(level=logging.DEBUG)


async def main(address):
    jura = await JuraBle.create(address)
    async with jura:
        print(await jura.about_machine())
        # print(await jura.lock_machine())
        # print("locked")
        # await asyncio.sleep(20)
        # print(await jura.unlock_machine())
        # print("unlocked")
        # print(await jura.statistics())
        # await jura.brew_product(
        #     0x02,
        #     strength=3,
        #     water=20,
        #     temperature=1,
        # )
        while True:
            await asyncio.sleep(1)
            print((await jura.product_progress()).hex())


asyncio.run(main(address))

# print(encode_decode(b"\x2a\x01", 0x2A).hex())
