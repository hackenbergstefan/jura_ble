# SPDX-FileCopyrightText: 2025 Stefan Hackenberg
#
# SPDX-License-Identifier: CC0-1.0

from jura_ble.classes import Machine


def test_read_master():
    machine = Machine("EF_MASTER")
    assert len(machine.products) > 0
    assert machine.product_properties["strength"].min == 1
    assert machine.product_properties["strength"].max == 10


def test_brew():
    machine = Machine("EF658S_C")
    prod = machine.products[0]
    assert prod.name == "Ristretto"
    assert prod.to_bytes() == bytes.fromhex(
        "01 02 04 19 01 00 02 01 00 00 00 00 00 00 00"
    )
