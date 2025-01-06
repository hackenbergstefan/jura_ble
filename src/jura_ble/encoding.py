# SPDX-FileCopyrightText: 2025 Jutta-Proto
# SPDX-FileCopyrightText: 2025 Stefan Hackenberg
#
# SPDX-License-Identifier: GPL-3.0-only

"""
Encodes and decodes data using proprietary algorithm in JURA protocol.

Copied from https://github.com/Jutta-Proto/protocol-bt-cpp/blob/0adb1ea802df13aac03262033706755f431f93b6/src/bt/ByteEncDecoder.cpp
"""

_NUMBERS1 = [14, 4, 3, 2, 1, 13, 8, 11, 6, 15, 12, 7, 10, 5, 0, 9]
_NUMBERS2 = [10, 6, 13, 12, 14, 11, 1, 9, 15, 7, 0, 5, 3, 2, 4, 8]


def shuffle(data_nibble, nibble_count, key_left_nibble, key_right_nibble):
    i5 = nibble_count >> 4
    tmp1 = _NUMBERS1[(data_nibble + nibble_count + key_left_nibble) % 16]
    tmp2 = _NUMBERS2[
        (tmp1 + key_right_nibble + i5 - nibble_count - key_left_nibble) % 16
    ]
    tmp3 = _NUMBERS1[
        (tmp2 + key_left_nibble + nibble_count - key_right_nibble - i5) % 16
    ]
    return (tmp3 - nibble_count - key_left_nibble) % 16


def encode_decode(data: bytes, key: int) -> bytes:
    result = bytearray()
    key_left_nibble = key >> 4
    key_right_nibble = key & 15
    nibble_count = 0
    for d in data:
        data_left_nibble = d >> 4
        data_right_nibble = d & 15
        result_left_nibble = shuffle(
            data_left_nibble, nibble_count, key_left_nibble, key_right_nibble
        )
        nibble_count += 1
        result_right_nibble = shuffle(
            data_right_nibble, nibble_count, key_left_nibble, key_right_nibble
        )
        nibble_count += 1
        result.append((result_left_nibble << 4) | result_right_nibble)
    return bytes(result)
