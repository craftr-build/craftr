# -*- coding: utf8 -*-
# Copyright (c) 2021 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import abc
import enum
import os
import posixpath
import re
import typing as t
from dataclasses import dataclass
from typing import Iterable, List, Optional, Union, TypeVar
from urllib.parse import urlparse

from ._version import bump_version, Version

T = TypeVar('T')


class VersionSelector(object):
  """
  Represents a version selector that limits which versions of a requirement can be
  picked. It simply wraps a string, but if the string looks like a semver selector,
  it can be converted into a ``setuptools`` compatible version selector string (see
  #to_setuptools()).
  """

  ANY: 'VersionSelector'

  def __init__(self, selector: t.Union[str, 'VersionSelector']):
    if isinstance(selector, VersionSelector):
      selector = selector._string
    self._string: str = selector.strip()

  def __str__(self):
    return str(self._string)

  def __repr__(self):
    return 'VersionSelector({!r})'.format(self._string)

  def __eq__(self, other):
    if type(self) == type(other):
      return self._string == other._string
    return False

  def __ne__(self, other):
    return not (self == other)

  def to_setuptools(self):  # type: () -> str
    """
    Converts the version selector to a string that Setuptools/Pip can understand by
    expanding the `~` and `^` range selectors.

    Given a version number X.Y.Z, the selectors will be expanded as follows:

    - `^X.Y.Z` -> `>=X.Y.Z,<X+1.0.0`
    - `~X.Y.Z` -> `>=X.Y.Z,<X.Y+1.0`
    - `X.Y.Z -> ==X.Y.Z`
    """

    # Poor-mans test if this looks like the form 'X.Y.Z' without anything around it.
    if not ',' in self._string and self._string[0].isdigit():
      return '==' + self._string

    regex = r'[~^](\d+\.\d+(\.\d+)?[.\-\w]*)'
    def sub(match):
      index = {'^': 0, '~': 1}[match.group(0)[0]]
      max_version = match.group(1).split('.')[:3]
      if len(max_version) == 2:
        max_version.append('0')
      if '-' in max_version[-1]:
        max_version[-1] = max_version[-1].partition('-')[0]
      max_version[index] = str(int(max_version[index]) + 1)
      for i in range(index+1, 3):
        max_version[i] = '0'
      return '>={},<{}'.format(match.group(1), '.'.join(max_version))

    s = self._string + '.0' * (3 - self._string.count('.') - 1)
    return re.sub(regex, sub, s)

  def is_semver_selector(self) -> bool:
    return bool(self._string and self._string[0] in '^~' and ',' not in self._string)

  def matches(self, version: Union[Version, str]) -> bool:
    if not self.is_semver_selector():
      # TODO (@NiklasRosenstein): Match setuptools version selectors.
      return False
    min_version = Version(self._string[1:])
    if self._string[0] == '^':
      max_version = bump_version(min_version, 'major')
    elif self._string[0] == '~':
      max_version = bump_version(min_version, 'minor')
    else:
      raise RuntimeError('invalid semver selector string {!r}'.format(self._string))
    return min_version <= Version(version) < max_version


VersionSelector.ANY = VersionSelector('*')


class BaseRequirement(abc.ABC):

  @abc.abstractclassmethod
  def from_string(cls, value: str) -> 'BaseRequirement': ...

  @abc.abstractmethod
  def __str__(self) -> str: ...

  @abc.abstractmethod
  def to_setuptools(self) -> str: ...


@dataclass
class Requirement(BaseRequirement):
  """
  A Requirement is simply combination of a package name and a version selector.
  """

  INVALID_CHARACTERS = '/&:;\'"!{}()%'

  package: str
  version: VersionSelector = VersionSelector.ANY
  extras: Optional[List[str]] = None

  def __str__(self, *, setuptools: bool = False):
    result = self.package
    if self.extras:
      result += '[' + ','.join(sorted(self.extras)) + ']'
    if self.version != VersionSelector.ANY:
      result += ' ' + (str(self.version.to_setuptools()) if setuptools else str(self.version))
    return result

  def __repr__(self):
    return repr(str(self))

  @classmethod
  def parse(cls, requirement_string: str) -> 'Requirement':
    error = ValueError('invalid requirement: {!r}'.format(requirement_string))
    if set(requirement_string) & set(cls.INVALID_CHARACTERS):
      raise error
    match = re.match(r'''
      ^\s*                # Allow leading whitespace
      ([\w\d\-\._]+)      # Package name
      (?:\[([^\]]+)\])?   # Package extras
      (?:\s*([^\[\]]+))?  # Version selector (do not allow brackets to avoid matching empty extras)
      $''', requirement_string, re.VERBOSE)
    if not match:
      raise error
    package, extras, version = match.groups()
    return cls(package, VersionSelector(version or VersionSelector.ANY),
      extras=sorted(map(str.strip, extras.split(','))) if extras else None)

  def to_setuptools(self) -> str:
    return self.__str__(setuptools=True)  # type: ignore

  @classmethod
  def from_string(cls, value: str) -> 'Requirement':
    return Requirement.parse(value)


@dataclass
class VendoredRequirement(BaseRequirement):
  """
  A vendored requirement is either a relative path or a string prefixed with `git+` that
  Pip understands as an installable source.
  """

  INVALID_CHARACTERS = '*&^;\'"!{}[]()%'

  class Type(enum.Enum):
    Git = enum.auto()
    Path = enum.auto()

  type: Type
  location: str

  def __post_init__(self):
    if self.type == self.Type.Path:
      self.location = self._normpath(self.location)

  def __str__(self):
    if self.type == self.Type.Git:
      return 'git+' + self.location
    elif self.type == self.Type.Path:
      return self._normpath(self.location)
    assert False, self.type

  @staticmethod
  def _normpath(path: str) -> str:
    """
    Normalizes a path in the way that it should be represented in the serialized form of the
    vendored requirement (as posix path).
    """

    if os.name == 'nt':
      path = path.replace('\\', '/')
    if not os.path.isabs(path):
      path = './' + posixpath.normpath(path)
    return path

  @classmethod
  def parse(cls, requirement_string: str, fallback_to_path: bool = False) -> 'VendoredRequirement':
    error = ValueError(f'invalid vendored requirement: {requirement_string!r}')
    if set(requirement_string) & set(cls.INVALID_CHARACTERS):
      raise error
    if requirement_string.startswith('git+'):
      url = requirement_string[4:]
      if not urlparse(url).scheme:
        raise error
      return cls(cls.Type.Git, url)
    result = urlparse(requirement_string)
    if result.scheme:
      raise error
    if not requirement_string.startswith('./') and not fallback_to_path:
      raise error
    return cls(cls.Type.Path, requirement_string)

  def to_setuptools(self) -> str:
    raise RuntimeError('VendoredRequirement is not supported in setuptools')

  def get_pip_args(self, root: str, develop: bool) -> List[str]:
    args = [self.location]
    if self.type == self.Type.Path:
      args[0] = os.path.normpath(os.path.join(root, args[0]))
      # We gotta make sure that Pip recognizes the argument as a path if there's no path
      # separator in there.
      if args[0].count(os.sep) == 0:
        args[0] = os.path.join(os.curdir, args[0])
      if develop:
        args.insert(0, '-e')
    return args

  @classmethod
  def from_string(cls, value: str) -> 'VendoredRequirement':
    return VendoredRequirement.parse(value)


class RequirementsList(List[Union[Requirement, VendoredRequirement]]):
  """
  A list of requirements. Provides some convenience methods.
  """

  def reqs(self) -> Iterable[Requirement]:
    return filter(lambda x: isinstance(x, Requirement), self)  # type: ignore

  def vendored_reqs(self) -> Iterable[VendoredRequirement]:
    return filter(lambda x: isinstance(x, VendoredRequirement), self)  # type: ignore

  def get_pip_args(self, root: str, develop: bool) -> List[str]:
    result = []
    for req in self.reqs():
      result.append(req.to_setuptools())
    for vreq in self.vendored_reqs():
      result += vreq.get_pip_args(root, develop)
    return result
