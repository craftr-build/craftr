
import typing as t
from collections.abc import Sequence
from pathlib import Path

from ._base import Property
from craftr.utils.beartype import beartype_check, beartype_validator

PathLike = t.Union[str, Path]


class PathProperty(Property[Path]):
  """
  A special property type for paths.
  """

  def __post_init__(self) -> None:
    assert self._base_type is None
    self._base_type = Path
    self._value_adapters.append(lambda x, r: beartype_check(PathLike, x))
    self._value_adapters.append(lambda x, r: Path(t.cast(PathLike, x)))


class PathListProperty(Property[list[Path]]):
  """
  A special property type for a list of paths.
  """

  def __post_init__(self) -> None:
    assert self._base_type is None
    self._base_type = list[Path]
    self._value_adapters.append(self._unpack_nested_properties)
    self._value_adapters.append(lambda l, r: beartype_check(Sequence[PathLike], l))
    self._value_adapters.append(lambda l, r: [Path(x) for x in t.cast(Sequence[PathLike], l)])

  @staticmethod
  def _unpack_nested_properties(value: object, references: list[Property]) -> object:
    if not isinstance(value, t.Sequence):
      return value
    copy = False
    for idx, item in enumerate(value):
      if isinstance(item, Property):
        if not copy:
          value = value[:]
          copy = True
        references.append(item)
        value[idx] = item.get()  # type: ignore
    return value

  def append(self, value: t.Union[PathLike, Sequence[PathLike], PathProperty, 'PathListProperty']) -> None:
    if isinstance(value, Property):
      references = self._references + [value]
      value = value.get()
    else:
      references = self._references

    if not isinstance(value, Sequence) or isinstance(value, str):
      value = [value]

    new_value = t.cast(list[PathLike], self.get()[:])
    new_value.extend(value)

    self.set(new_value)  # type: ignore
    self._references = references

  def clear(self) -> None:
    self.set([])
