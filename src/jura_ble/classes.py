from dataclasses import dataclass
from datetime import date
from typing import Optional


def decode_date(date_value: int) -> date:
    year = ((date_value & 0xFE00) >> 9) + 1990
    month = (date_value & 0x1E0) >> 5
    day = date_value & 0x1F
    return date(year, 1 + month, 1 + day)


@dataclass
class MachineData:
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
