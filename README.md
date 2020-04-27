## Dephell Specifier

[![travis](https://travis-ci.org/dephell/dephell_specifier.svg?branch=master)](https://travis-ci.org/dephell/dephell_specifier)
[![MIT License](https://img.shields.io/pypi/l/dephell-specifier.svg)](https://github.com/dephell/dephell_specifier/blob/master/LICENSE)

Work with version specifiers.

Supported specifiers:

+ [PEP-440](https://www.python.org/dev/peps/pep-0440/).
+ [NPM SemVer](https://github.com/npm/node-semver).
+ [Maven](http://maven.apache.org/enforcer/enforcer-rules/versionRanges.html).
+ [RubyGems](https://guides.rubygems.org/patterns/)

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
