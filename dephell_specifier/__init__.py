"""A package to work with version specifiers.

Supports PEP-440, SemVer, Ruby, NPM, and Maven specifier formats.
"""
from __future__ import annotations

from .git_specifier import GitSpecifier
from .range_specifier import RangeSpecifier
from .specifier import Specifier


__version__ = '0.3.0'
__all__ = ['GitSpecifier', 'RangeSpecifier', 'Specifier']
