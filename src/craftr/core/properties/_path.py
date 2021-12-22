
import typing as t
import typing_extensions as te
from collections.abc import Sequence
from pathlib import Path

from beartype import beartype
from craftr.utils.beartype import beartype_validator
from ._base import BaseProperty

PathLike = t.Union[str, Path]

_PathPropertyBase = BaseProperty[
  Path,
  t.Union[PathLike, BaseProperty[Path, t.Any]]
]

_PathListPropertyBase = BaseProperty[
  list[Path],
  t.Union[PathLike, BaseProperty[Path, t.Any], Sequence[t.Union[PathLike, BaseProperty[Path, t.Any]]]]
]


class _HasOutputAttribute:

  def __init__(self, is_output: bool = False) -> None:
    self.is_output = is_output


class PathProperty(_PathPropertyBase, _HasOutputAttribute):
  """
  A special property type for paths.
  """

  def __post_init__(self) -> None:
    assert self._base_type is None
    self._base_type = Path

    # Configure additional validators for values that can be pushed into the property.
    validator = beartype_validator(PathLike)
    self._value_adapters.append(lambda x, r: validator(x))
    self._value_adapters.append(lambda x, r: Path(t.cast(PathLike, x)))


class PathListProperty(_PathListPropertyBase, _HasOutputAttribute):
  """
  A special property type for a list of paths.
  """

  def __post_init__(self) -> None:
    assert self._base_type is None
    self._base_type = list[Path]
    validator = beartype_validator(Sequence[PathLike])
    self._value_adapters.append(self._unpack_nested_properties)
    self._value_adapters.append(lambda l, r: validator(l))
    self._value_adapters.append(lambda l, r: [Path(x) for x in t.cast(Sequence[PathLike], l)])

  @staticmethod
  def _unpack_nested_properties(value: t.Any, references: list[BaseProperty]) -> t.Any:
    if not isinstance(value, t.Sequence):
      return value
    copy = False
    for idx, item in enumerate(value):
      if isinstance(item, BaseProperty):
        if not copy:
          value = value[:]
          copy = True
        references.append(item)
        value[idx] = item.get()  # type: ignore
    return value

  def append(self, value: t.Union[PathLike, Sequence[PathLike], PathProperty, 'PathListProperty']) -> None:
    if isinstance(value, BaseProperty):
      references = self._references + [value]
      value = value.get()
    else:
      references = self._references

    if not isinstance(value, Sequence) or isinstance(value, str):
      value = [value]

    new_value = t.cast(list[PathLike], self.get()[:])
    new_value.extend(value)

    self.set(new_value)  # ty pe: ignore
    self._references = references

  def clear(self) -> None:
    self.set([])


def is_path_property(property: BaseProperty) -> te.TypeGuard[t.Union[PathProperty, PathListProperty]]:
  return isinstance(property, (PathProperty, PathListProperty))


def get_path_property_paths(property: t.Union[PathProperty, PathListProperty]) -> list[Path]:
  if isinstance(property, PathProperty):
    return [property.get()]
  elif isinstance(property, PathListProperty):
    return property.get()
  else:
    assert False
