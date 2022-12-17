"""A package to work with version specifiers.

Supports PEP-440, SemVer, Ruby, NPM, and Maven specifier formats.
"""
from .git_specifier import GitSpecifier
from .range_specifier import RangeSpecifier
from .specifier import Specifier


__version__ = '0.2.2'
__all__ = ['GitSpecifier', 'RangeSpecifier', 'Specifier']
