import pytest
from dephell_specifier import Specifier


@pytest.mark.parametrize('left, right, result', [
    # left
    ('<1.2',    '<1.4',     '<1.2'),
    ('<1.2',    '<=1.4',    '<1.2'),
    ('<=1.2',    '<1.4',    '<=1.2'),
    ('<=1.2',    '<=1.4',   '<=1.2'),

    # swap is not important
    ('<1.4',    '<1.2',     '<1.2'),
    ('<=1.4',   '<1.2',     '<1.2'),
    ('<1.4',    '<=1.2',    '<=1.2'),
    ('<=1.4',   '<=1.2',    '<=1.2'),

    # right
    ('>1.2',    '>1.4',     '>1.4'),
    ('>=1.2',   '>1.4',     '>1.4'),
    ('>1.2',    '>=1.4',    '>=1.4'),
    ('>=1.2',   '>=1.4',    '>=1.4'),

    # equal
    ('==1.2',   '<1.4',     '==1.2'),
    ('==1.2',   '<=1.4',    '==1.2'),
    ('>=1.2',   '==1.4',    '==1.4'),
    ('>1.2',    '==1.4',    '==1.4'),

    # common version
    ('==1.2',   '==1.2',    '==1.2'),
    ('<=1.2',   '==1.2',    '==1.2'),
    ('>=1.2',   '==1.2',    '==1.2'),
    ('<=1.2',   '>=1.2',    '==1.2'),

    # empty interval
    ('<=1.2',   '>=1.4',    None),
    ('<=1.2',   '>1.4',     None),
    ('<1.2',    '>=1.4',    None),
    ('==1.2',   '>=1.4',    None),
    ('==1.2',   '>1.4',     None),
    ('<=1.2',   '==1.4',    None),
    ('<1.2',    '==1.4',    None),

    # closed interval
    ('>=1.2',   '<=1.4',    None),
    ('>1.2',    '<1.4',     None),
    ('>=1.2',   '<1.4',     None),
    ('>1.2',    '<=1.4',    None),
])
def test_merge(left, right, result):
    ls = Specifier(left)
    rs = Specifier(right)
    if result is None:
        with pytest.raises(TypeError):
            ls + rs
    else:
        merged = ls + rs
        assert str(merged) == result
