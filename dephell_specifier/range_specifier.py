# external
from packaging.specifiers import InvalidSpecifier
from packaging.version import LegacyVersion, parse, Version

# app
from .constants import PYTHONS, JoinTypes
from .git_specifier import GitSpecifier
from .specifier import Specifier


class RangeSpecifier:

    def __init__(self, spec=None):
        if not spec:
            self._specs = set()
            self.join_type = JoinTypes.AND
            return

        subspecs = str(spec).split('||')
        if len(subspecs) > 1:
            self._specs = {type(self)(subspec) for subspec in subspecs}
            self.join_type = JoinTypes.OR
            return

        self._specs = self._parse(spec)
        self.join_type = JoinTypes.AND
        return

    @staticmethod
    def _parse(spec) -> set:
        if not isinstance(spec, (list, tuple)):
            spec = str(spec).split(',')
        result = set()
        for constr in spec:
            constr = constr.strip()
            if constr in ('', '*'):
                continue
            constr = constr.replace('.x', '.*')
            constr = constr.replace('.X', '.*')

            # https://docs.npmjs.com/misc/semver#advanced-range-syntax

            if ' - ' in constr:
                if '.*' in constr:
                    raise InvalidSpecifier('cannot mix ranges and starred notation')
                left, right = constr.split(' - ', maxsplit=1)
                result.add(Specifier('>=' + left))
                result.add(Specifier('<=' + right))
                continue

            if constr[0] in '~^':
                version = parse(constr.lstrip('~^=').replace('.*', '.0'))
                if isinstance(version, LegacyVersion):
                    raise InvalidSpecifier(constr)
                parts = version.release + (0, 0)
                parts = tuple(map(str, parts))
                left = '.'.join(parts[:3])

                if constr[:2] == '~=':    # ~=1.2 := >=1.2 <2.0;  ~=1.2.2 := >=1.2.2 <1.3.0
                    if len(version.release) == 1:
                        msg = '`~=` MUST NOT be used with a single segment version: '
                        raise ValueError(msg + str(version))
                    # https://www.python.org/dev/peps/pep-0440/#compatible-release
                    right = '.'.join(map(str, version.release[:3][:-1])) + '.*'
                elif constr[0] == '^':    # ^1.2.3 := >=1.2.3 <2.0.0
                    # https://www.npmjs.com/package/semver#caret-ranges-123-025-004
                    right = '.'.join([parts[0], '*'])
                elif constr[0] == '~':  # ~1.2.3 := >=1.2.3 <1.3.0
                    # https://www.npmjs.com/package/semver#tilde-ranges-123-12-1
                    right = '.'.join([parts[0], parts[1], '*'])

                result.add(Specifier('>=' + left))
                result.add(Specifier('==' + right))
                continue

            result.add(Specifier(constr))
        return result

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
