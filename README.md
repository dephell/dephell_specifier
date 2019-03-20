## Dephell Specifier

Work with version specifiers.

## Installation

Install from [PyPI](https://pypi.org/project/dephell-specifier/):

```bash
python3 -m pip install --user dephell_specifier
```

## Usage

```python
from dephell_specifier import RangeSpecifier

'3.4' in RangeSpecifier('*')
# True

'3.4' in RangeSpecifier('<=2.7')
# False

'3.4' in RangeSpecifier('>2.7')
# True

'3.4' in RangeSpecifier('>2.7,<=3.4')
# True

'3.4' in RangeSpecifier('<2.7 || >=3.4')
# True
```
