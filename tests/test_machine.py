# SPDX-FileCopyrightText: 2025 Stefan Hackenberg
#
# SPDX-License-Identifier: CC0-1.0


from jura_ble import ProductProgress, ProductProgressState
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
        "01 02 04 05 01 00 02 01 00 00 00 00 00 00 00"
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


def test_decode_product_progress():
    progress = ProductProgress(
        bytes.fromhex("2a 34 04 04 04 00 0e 01 01 09 12 11 00 00 11 00 00 00 00 00")
    )
    assert progress.state == ProductProgressState.MILK_FOAM_VOLUME
    assert progress.coffee_strength == (4, 4)
    assert progress.water_volume == (0, 0xE)
    assert progress.milk_time == (1, 1)
    assert progress.milk_foam == (9, 0x12)
    assert progress.water_temperature == 0x11
    assert progress.pause_time == 0
    assert progress.intake_percentage == 0x11
    assert progress.valid is True

    assert (
        ProductProgress(
            bytes.fromhex("2a 3e 04 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00")
        ).state
        == ProductProgressState.LAST_PROGRESS_STATE
    )
