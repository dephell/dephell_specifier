import re
from typing import Set, List

# external
from packaging.specifiers import InvalidSpecifier
from packaging.version import LegacyVersion, parse, Version

# app
from .constants import PYTHONS, JoinTypes, OPERATOR_SYMBOLS
from .git_specifier import GitSpecifier
from .specifier import Specifier


REX_MAVEN_INTERVAL = re.compile(r'([\]\)])\,([\[\(])')
REX_TRIM_OPERATOR = re.compile(r'([{}])\s+'.format(re.escape(OPERATOR_SYMBOLS)))


class RangeSpecifier:

    def __init__(self, spec=None):
        if not spec:
            self._specs = set()
            self.join_type = JoinTypes.AND
            return

        # split `>2 || <1` on `>2` and `<1`
        subspecs = str(spec).split('||')
        if len(subspecs) > 1:
            self._specs = {type(self)(subspec) for subspec in subspecs}
            self.join_type = JoinTypes.OR
            return

        # split `(,1),(2,)` on `(,1)` and `(2,)`
        subspecs = REX_MAVEN_INTERVAL.sub(r'\1|\2', str(spec)).split('|')
        if len(subspecs) > 1:
            self._specs = {type(self)(subspec) for subspec in subspecs}
            self.join_type = JoinTypes.OR
            return

        self._specs = self._parse(spec)
        self.join_type = JoinTypes.AND
        return

    @classmethod
    def _parse(cls, spec) -> Set[Specifier]:
        spec = cls._split_specifier(spec)
        result = set()
        for constr in spec:
            constr = cls._clean_constraint(constr)
            if not constr:
                continue
            # parse npm's version range (`1.2.3 - 2.3.0`)
            if ' - ' in constr:
                if '.*' in constr:
                    raise InvalidSpecifier('cannot mix ranges and starred notation')
                left, right = constr.split(' - ', maxsplit=1)
                result.add(Specifier('>=' + left))
                result.add(Specifier('<=' + right))
                continue
            # parse mixed stars and operators like `<=1.2.*`
            if constr[0] in '<>' and '.*' in constr:
                result.add(cls._parse_star_and_operator(constr))
                continue
            # parse npm-style semver specifiers
            if constr[0] in '~^':
                result.update(cls._parse_npm(constr))
                continue
            # parse maven-style interval specifiers
            if constr[0] in '[(' or constr[-1] in ')]':
                result.update(cls._parse_maven(constr))
                continue
            # parse classic python specifier
            result.add(Specifier(constr))
        return result

    @staticmethod
    def _split_specifier(spec) -> List[str]:
        if isinstance(spec, (list, tuple)):
            return list(spec)
        spec = str(spec)

        # pep-style comma-separated
        if ',' in spec:
            return spec.split(',')

        # single specifier
        spec = REX_TRIM_OPERATOR.sub(r'\1', spec)
        if ' ' not in spec:
            return [spec]

        # npm-style space-separated
        spec = spec.replace(' - ', '|').split()
        spec = [constr.replace('|', ' - ') for constr in spec]
        return spec

    @staticmethod
    def _clean_constraint(constr: str) -> str:
        constr = constr.strip()
        if constr in ('', '*'):
            return ''
        constr = constr.replace('.x', '.*')
        constr = constr.replace('.X', '.*')
        constr = constr.replace('.*.*', '.*')
        if constr.lstrip(OPERATOR_SYMBOLS).lower() in ('x', '*'):
            return ''

        # add operator to constraint without operator
        if ' - ' in constr:
            return constr
        if constr[0] not in OPERATOR_SYMBOLS and constr[-1] not in OPERATOR_SYMBOLS:
            constr = '==' + constr
        # replace `=` operator by `==`
        if len(constr) > 1 and constr[0] == '=' and constr[1] not in OPERATOR_SYMBOLS:
            constr = '==' + constr[1:]
        return constr

    @staticmethod
    def _parse_star_and_operator(constr: str) -> Specifier:
        if constr[:2] in {'<', '>', '>='}:
            return Specifier(constr.replace('.*', '.0'))

        version = parse(constr.lstrip(OPERATOR_SYMBOLS).rstrip('.*'))
        parts = version.release[:-1] + (version.release[-1] + 1, )
        return Specifier(constr[:2] + '.'.join(map(str, parts)))

    @staticmethod
    def _parse_maven(constr: str) -> Set[Specifier]:
        if constr in '[]()':
            return set()
        if constr[0] == '[' and constr[-1] == ']':
            return {Specifier('==' + constr[1:-1])}
        if constr[0] == '[':
            return {Specifier('>=' + constr[1:])}
        if constr[0] == '(':
            return {Specifier('>' + constr[1:])}
        if constr[-1] == ']':
            return {Specifier('<=' + constr[:-1])}
        if constr[-1] == ')':
            return {Specifier('<' + constr[:-1])}
        raise ValueError('non maven constraint: {}'.format(constr))

    @staticmethod
    def _parse_npm(constr: str) -> Set[Specifier]:
        version = parse(constr.lstrip(OPERATOR_SYMBOLS).replace('.*', '.0'))
        if isinstance(version, LegacyVersion):
            raise InvalidSpecifier(constr)
        parts = version.release + (0, 0)
        parts = tuple(map(str, parts))

        if constr[:2] == '~=':    # ~=1.2 := >=1.2 <2.0;  ~=1.2.2 := >=1.2.2 <1.3.0
            if len(version.release) == 1:
                msg = '`~=` MUST NOT be used with a single segment version: '
                raise ValueError(msg + str(version))
            # https://www.python.org/dev/peps/pep-0440/#compatible-release
            right = '.'.join(map(str, version.release[:3][:-1])) + '.*'
        elif constr[0] == '^':    # ^1.2.3 := >=1.2.3 <2.0.0
            # https://www.npmjs.com/package/semver#caret-ranges-123-025-004
            right = '.'.join([parts[0], '*'])
        elif constr[0] == '~':  # ~1.2.3 (or ~>1.2.3 for ruby) := >=1.2.3 <1.3.0
            # https://www.npmjs.com/package/semver#tilde-ranges-123-12-1
            # https://thoughtbot.com/blog/rubys-pessimistic-operator
            if len(version.release) == 1:
                right = '{}.*'.format(version.release[0])
            else:
                right = '.'.join([parts[0], parts[1], '*'])

        left = '.'.join(parts[:3])
        return {Specifier('>=' + left), Specifier('==' + right)}

    def attach_time(self, releases) -> bool:
        """Attach time to all specifiers if possible
        """
        ok = False
        for spec in self._specs:
            if spec.time is None:
                attached = spec.attach_time(releases)
                if attached:
                    ok = True
        return ok

    def to_marker(self, name: str, *, wrap: bool = False) -> str:
        sep = ' and ' if self.join_type == JoinTypes.AND else ' or '
        marker = sep.join([spec.to_marker(name, wrap=True) for spec in sorted(self._specs)])
        if len(self._specs) == 1:
            wrap = False
        if wrap:
            marker = '(' + marker + ')'
        return marker

    def copy(self) -> 'RangeSpecifier':
        new = type(self)()
        new._specs = self._specs.copy()
        new.join_type = self.join_type
        return new

    def peppify(self) -> 'RangeSpecifier':
        """Returns python specifier without `||`
        """
        if self.join_type == JoinTypes.AND:
            return self
        pythons = sorted(Version(python) for python in PYTHONS)

        # get left boundary
        left = None
        for python in pythons:
            if python in self:
                left = python
                break

        # get right boundary
        right = None
        excluded = []
        for python in pythons:
            if python in self:
                right = python
            elif left is None or python > left:
                excluded.append(python)
        if right is not None:
            right = (pythons + [None])[pythons.index(right) + 1]

        # get excluded intervals
        if right is not None:
            excluded = [python for python in excluded if python < right]
        excluded = ','.join('!={}.*'.format(python) for python in excluded)
        if excluded:
            excluded = ',' + excluded

        # combine it into specifier
        if left is None and right is None:
            return type(self)(excluded[1:])
        if left is None:
            return type(self)('<' + str(right) + excluded)
        if right is None:
            return type(self)('>=' + str(left) + excluded)
        return type(self)('>={},<{}'.format(left, right) + excluded)

    # properties

    @property
    def python_compat(self) -> bool:
        for version in PYTHONS:
            if version in self:
                return True
        return False

    # magic methods

    def __add__(self, other):
        new = self.copy()
        attached = new._attach(other)
        if attached:
            return new
        return NotImplemented

    def __radd__(self, other):
        new = self.copy()
        attached = new._attach(other)
        if attached:
            return new
        return NotImplemented

    def __iadd__(self, other):
        attached = self._attach(other)
        if attached:
            return self
        return NotImplemented

    def _attach(self, other) -> bool:
        if isinstance(other, GitSpecifier):
            self._specs.add(other)
            return True
        if not isinstance(other, type(self)):
            return False

        # and + and
        if self.join_type == other.join_type == JoinTypes.AND:
            self._specs.update(other._specs)
            return True

        # and + or
        if self.join_type == JoinTypes.AND:
            and_specs = self._specs
            or_specs = other._specs
            new_specs = set()
            for or_spec in or_specs:
                new = type(self)()
                new._specs = {or_spec} | and_specs
                new_specs.add(new)
            self._specs = new_specs
            self.join_type = JoinTypes.OR
            return True

        # or + and
        if other.join_type == JoinTypes.AND:
            and_specs = other._specs
            or_specs = self._specs
            new_specs = set()
            for or_spec in or_specs:
                new = type(self)()
                new._specs = {or_spec} | and_specs
                new_specs.add(new)
            self._specs = new_specs
            return True

        # or + or
        left_specs = self._specs
        right_specs = other._specs
        new_specs = set()
        for left_spec in left_specs:
            for right_spec in right_specs:
                new = type(self)()
                new._specs = {left_spec, right_spec}
                new_specs.add(new)
        self._specs = new_specs
        return True

    def __contains__(self, release) -> bool:
        rule = all if self.join_type == JoinTypes.AND else any
        return rule((release in specifier) for specifier in self._specs)

    def __str__(self):
        if not self._specs:
            return ''
        sep = ',' if self.join_type == JoinTypes.AND else ' || '
        return sep.join(sorted(map(str, self._specs)))

    def __repr__(self):
        return '{name}({spec})'.format(
            name=self.__class__.__name__,
            spec=str(self),
        )

    def __bool__(self):
        return bool(self._specs)

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            return False
        return str(self) < str(other)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return str(self) == str(other)

    def __hash__(self):
        return hash(str(self))
