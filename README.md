<!--
SPDX-FileCopyrightText: 2025 Stefan Hackenberg

SPDX-License-Identifier: CC0-1.0
-->

# jura-ble

This project is a pure Python implementation of [Jutta-Proto/protocol-bt-cpp](https://github.com/Jutta-Proto/protocol-bt-cpp/).

## Installation

```bash
pip install git+https://github.com/hackenbergstefan/jura_ble@v1.0.0
```

## Usage

```python
from jura_ble import JuraBle

jura = JuraBle.create()
async with jura:
    print(jura.machine_status())
```

## License

This project is licensed under GPL-3.0 License - see the [LICENSE](LICENSE) file for details.
