# built-in
from enum import Enum, unique


@unique
class JoinTypes(Enum):
    AND = 1
    OR = 2


PYTHONS_DEPRECATED = ('2.6', '2.7', '3.0', '3.1', '3.2', '3.3', '3.4')
PYTHONS_POPULAR = ('3.5', '3.6', '3.7')
PYTHONS_UNRELEASED = ('3.8', '4.0')
PYTHONS = PYTHONS_POPULAR + PYTHONS_DEPRECATED + PYTHONS_UNRELEASED

OPERATOR_SYMBOLS = '!><=[]()~^,'
