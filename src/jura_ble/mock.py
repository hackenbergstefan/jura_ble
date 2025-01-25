# SPDX-FileCopyrightText: 2025 Stefan Hackenberg
#
# SPDX-License-Identifier: GPL-3.0-only

import time
from typing import Optional
from unittest.mock import AsyncMock

from jura_ble.machine import Machine

from . import CoffeeProduct, JuraBle


class JuraBleMock(JuraBle):
    @staticmethod
    async def create(model: str, address: Optional[str] = None, timeout: int = 20):
        return JuraBleMock(model, address="", key=0, timeout=timeout)

    def __init__(self, model: str, address: str, key: int, *, timeout: int = 20):
        self.model = Machine(model)
        self.client = AsyncMock()
        self.key = key
        self._heartbeat_task = None
        self.brewing_started = None

    async def _write(self, characteristic, data, encoded=True, prepend_key=True):
        return None

    async def _read(self, characteristic: str, *, encoded: bool = True):
        return 50 * b"\x00"

    async def brew_product(self, product: CoffeeProduct):
        self.brewing_started = time.time()
        await super().brew_product(product)

    async def product_progress(self) -> dict[str, bytes | int] | None:
        if self.brewing_started is None:
            return None
        if time.time() - self.brewing_started > 10:
            self.brewing_started = None
            return None
        return {
            "step": time.time() - self.brewing_started,
            "product": 1,
            "rest": 12 * b"\x01",
        }
