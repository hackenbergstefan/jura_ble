# SPDX-FileCopyrightText: 2025 Stefan Hackenberg
#
# SPDX-License-Identifier: CC0-1.0


from jura_ble.machine import Machine, bytes_to_bits


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


def test_decode_status():
    machine = Machine("EF658S_C")
    assert machine.decode_status(
        bytes_to_bits(bytes.fromhex("2a00040000000000000000000000000000000004")[1:9])
    ) == ["coffee ready"]
    assert machine.decode_status(
        bytes_to_bits(bytes.fromhex("2a04000000000000000000000000000000000006")[1:9])
    ) == ["outlet missing"]
    assert (
        machine.decode_status(
            bytes_to_bits(
                bytes.fromhex("2a00000000000000000000000000000000000004")[1:9]
            )
        )
        == []
    )
