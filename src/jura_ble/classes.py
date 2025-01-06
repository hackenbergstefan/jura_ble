# SPDX-FileCopyrightText: 2025 Jutta-Proto
# SPDX-FileCopyrightText: 2025 Stefan Hackenberg
#
# SPDX-License-Identifier: GPL-3.0-only

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET


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

    def value_str(self, value: int) -> str | None:
        if self.value_mapping is not None:
            return self.value_mapping[value]
        return None

    def valid(self, value: int) -> bool:
        return self.min <= value <= self.max and value % self.step == 0


PRODUCT_PROPERTIES = {
    prop.name: prop
    for prop in [
        ProductProperty(
            name="strength",
            xml_name="COFFEE_STRENGTH",
            min=1,
            max=5,
            argument_number=3,
            value_mapping={
                1: "XMild",
                2: "Mild",
                3: "Normal",
                4: "Strong",
                5: "XStrong",
            },
        ),
        ProductProperty(
            name="grinder_ratio",
            xml_name="GRINDER_RATIO",
            min=0,
            max=4,
            argument_number=2,
            value_mapping={0: "100_0", 1: "75_25", 2: "50_50", 3: "25_75", 4: "0_100"},
        ),
        ProductProperty(
            name="water",
            xml_name="WATER_AMOUNT",
            min=25,
            max=290,
            step=5,
            argument_number=4,
        ),
        ProductProperty(
            name="temperature",
            xml_name="TEMPERATURE",
            min=0,
            max=2,
            argument_number=7,
            value_mapping={1: "Low", 2: "Normal", 3: "High"},
        ),
        ProductProperty(
            name="water_bypass",
            xml_name="BYPASS",
            argument_number=10,
            min=0,
            max=580,
            step=5,
        ),
        ProductProperty(
            name="milk_foam",
            xml_name="MILK_FOAM_AMOUNT",
            argument_number=6,
            min=0,
            max=120,
        ),
        ProductProperty(
            name="milk",
            xml_name="MILK_AMOUNT",
            argument_number=5,
            min=0,
            max=120,
        ),
        ProductProperty(
            name="milk_break",
            xml_name="MILK_BREAK",
            argument_number=11,
            min=0,
            max=120,
        ),
    ]
}


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


def load_products(xmlfile: str | Path) -> list[CoffeeProduct]:
    """
    Load coffee products from an XML file.

    Check [Machine Files](https://github.com/Jutta-Proto/protocol-bt-cpp/tree/main?tab=readme-ov-file#machine-files).
    """
    xmlfile = Path(xmlfile)

    root = ET.parse(xmlfile).getroot()
    products = []
    for product in root.findall(".//{*}PRODUCT"):
        code = int(product.attrib["Code"], base=16)
        name = product.attrib["Name"]
        properties = {
            prop.name: int(
                product_property.attrib.get(
                    "Value", product_property.attrib.get("Default", 0)
                )
            )
            if (product_property := product.find(f"{{*}}{prop.xml_name}")) is not None
            else 0
            for prop in PRODUCT_PROPERTIES.values()
        }
        products.append(CoffeeProduct(code=code, name=name, **properties))
    return products
