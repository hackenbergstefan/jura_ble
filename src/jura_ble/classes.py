# SPDX-FileCopyrightText: 2025 Jutta-Proto
# SPDX-FileCopyrightText: 2025 Stefan Hackenberg
#
# SPDX-License-Identifier: GPL-3.0-only

from dataclasses import dataclass
from datetime import date
from typing import Optional


def decode_date(date_value: int) -> date:
    """Decode a date value from jura binary format."""
    year = ((date_value & 0xFE00) >> 9) + 1990
    month = (date_value & 0x1E0) >> 5
    day = date_value & 0x1F
    return date(year, 1 + month, 1 + day)


@dataclass
class MachineData:
    """Machine data as dataclass."""

    key: int
    bf_maj_ver: int
    bf_min_ver: int
    article_number: int
    machine_number: int
    serial_number: int
    machine_prod_date: date
    machine_prod_date_uchi: date
    status_bits: int
    bf_ver_str: Optional[str] = None
    coffee_machine_ver_str: Optional[str] = None
    last_connected_tablet_id: Optional[int] = None

    @staticmethod
    def from_bytes(data: bytes) -> "MachineData":
        key = data[0]
        bf_maj_ver = data[1]
        bf_min_ver = data[2]
        article_number = int.from_bytes(data[4:6], "little")
        machine_number = int.from_bytes(data[6:8], "little")
        serial_number = int.from_bytes(data[8:10], "little")
        machine_prod_date = decode_date(int.from_bytes(data[10:12], "little"))
        machine_prod_date_uchi = decode_date(int.from_bytes(data[12:14], "little"))
        status_bits = data[15]

        bf_ver_str = data[27:35].decode("ascii").strip() if len(data) > 27 else None
        coffee_machine_ver_str = (
            data[35:52].decode("ascii").strip() if len(data) > 35 else None
        )
        last_connected_tablet_id = (
            int.from_bytes(data[51:55], "little") if len(data) > 51 else None
        )

        return MachineData(
            key=key,
            bf_maj_ver=bf_maj_ver,
            bf_min_ver=bf_min_ver,
            article_number=article_number,
            machine_number=machine_number,
            serial_number=serial_number,
            machine_prod_date=machine_prod_date,
            machine_prod_date_uchi=machine_prod_date_uchi,
            status_bits=status_bits,
            bf_ver_str=bf_ver_str,
            coffee_machine_ver_str=coffee_machine_ver_str,
            last_connected_tablet_id=last_connected_tablet_id,
        )


@dataclass
class ProductProperty:
    name: str
    xml_name: str
    argument_number: int
    min: int
    max: int
    step: int = 1
    value_mapping: Optional[dict[int, str]] = None

    SUPPORTED_PROPERTIES = {
        "GRINDER_RATIO": "grinder_ratio",
        "COFFEE_STRENGTH": "strength",
        "WATER_AMOUNT": "water",
        "MILK_AMOUNT": "milk",
        "MILK_FOAM_AMOUNT": "milk_foam",
        "TEMPERATURE": "temperature",
        "STROKE": "stroke",
        "BYPASS": "water_bypass",
        "MILK_BREAK": "milk_break",
    }

    def value_str(self, value: int) -> str | None:
        if self.value_mapping is not None:
            return self.value_mapping[value]
        return None

    def valid(self, value: int) -> bool:
        return self.min <= value <= self.max and value % self.step == 0


@dataclass
class CoffeeProduct:
    code: int
    name: str
    strength: int
    grinder_ratio: int
    water: int
    temperature: int
    water_bypass: int
    milk_foam: int
    milk: int
    milk_break: int
    stroke: int

    _props: dict[str, ProductProperty]

    def to_bytes(self) -> bytes:
        """
        Convert the coffee product to bytes.

        According to [Brewing Coffee](https://github.com/Jutta-Proto/protocol-bt-cpp/tree/main?tab=readme-ov-file#brewing-coffee)
        the total number of bytes is 15.
        """
        byts = bytearray([self.code]) + 14 * b"\x00"
        for prop in self._props.values():
            byts[prop.argument_number - 1] = getattr(self, prop.name) // prop.step
        return bytes(byts)
