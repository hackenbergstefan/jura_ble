# SPDX-FileCopyrightText: 2025 Jutta-Proto
# SPDX-FileCopyrightText: 2025 Stefan Hackenberg
#
# SPDX-License-Identifier: GPL-3.0-only

import io
import zipfile
from xml.etree import ElementTree as ET

import requests

from .classes import CoffeeProduct, ProductProperty

"""
Machine related data found in XML files.
"""

PRODUCTS_URL = "https://github.com/AlexxIT/Jura/raw/refs/tags/v1.1.0/custom_components/jura/core/resources.zip"
"""URL to download the product XML files."""


def download_product_xml(product_name: str) -> ET.ElementTree:
    """
    Download and open the product XML file from the Homeassist repository.

    The product XML files are stored in a ZIP file.
    """
    r = requests.get(PRODUCTS_URL, stream=True)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        product_file = [
            file
            for file in z.infolist()
            if product_name in file.filename and file.filename.endswith(".xml")
        ][0]
        with z.open(product_file) as f:
            return ET.parse(f)


def load_properties(xml: ET.Element) -> dict[str, ProductProperty]:
    """Load product properties from XML."""
    product_properties = {}
    for xml_name, name in ProductProperty.SUPPORTED_PROPERTIES.items():
        xml_prop = xml.find(f".//{{*}}{xml_name}")
        argument_number = int(xml_prop.attrib["Argument"][1:])
        if len(xml_prop) > 0:
            # Load value mapping
            value_mapping = {
                int(value.attrib["Value"], 16): value.attrib["Name"]
                for value in xml_prop.findall(".//{*}ITEM")
            }
            prop = ProductProperty(
                name=name,
                xml_name=xml_name,
                argument_number=argument_number,
                min=min(value_mapping.keys()),
                max=max(value_mapping.keys()),
                value_mapping=value_mapping,
            )
        else:
            prop = ProductProperty(
                name=name,
                xml_name=xml_name,
                argument_number=argument_number,
                min=int(xml_prop.attrib["Min"]),
                max=int(xml_prop.attrib["Max"]),
                step=int(xml_prop.attrib.get("Step", 1)),
            )
        product_properties[name] = prop
    return product_properties


def load_products(
    xml: ET.Element, product_properties: dict[str, ProductProperty]
) -> list[CoffeeProduct]:
    """Load products from XML."""
    products = []
    for product in xml.findall(".//{*}PRODUCT"):
        code = int(product.attrib["Code"], base=16)
        name = product.attrib["Name"]
        properties = {
            prop.name: int(
                product_property.attrib.get(
                    "Value", product_property.attrib.get("Default", prop.min)
                )
            )
            if (product_property := product.find(f"{{*}}{prop.xml_name}")) is not None
            else prop.min
            for prop in product_properties.values()
        }
        products.append(
            CoffeeProduct(
                code=code,
                name=name,
                _props=product_properties,
                **properties,
            )
        )
    return products


def load_status_bits(xml: ET.Element) -> dict[int, str]:
    """Load status bits from XML."""
    status_bits = {}
    for status in xml.findall(".//{*}ALERT"):
        status_bits[int(status.attrib["Bit"])] = status.attrib["Name"]
    return status_bits


def bytes_to_bits(data: bytes) -> list[int]:
    """Convert a byte array to a list of bits."""
    return [int(bit) for byte in data for bit in f"{byte:08b}"]


class Machine:
    def __init__(self, model: str):
        self.model = model

        xml = download_product_xml(self.model).getroot()
        self.product_properties = load_properties(xml)
        self.products = load_products(xml, self.product_properties)
        self.status_bits = load_status_bits(xml)

    def decode_status(self, status: list[int]) -> list[str]:
        """Return a list of status messages from the status bits."""
        return [name for bit, name in self.status_bits.items() if status[bit] != 0]
