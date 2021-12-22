
import typing as t
from collections.abc import Sequence
from pathlib import Path

from beartype import beartype
from craftr.utils.beartype import beartype_validator
from ._base import BaseProperty

PathLike = t.Union[str, Path]


class _HasOutputAttribute:

  def __init__(self, is_output: bool = False) -> None:
    self.is_output = is_output


class PathProperty(BaseProperty[Path, PathLike], _HasOutputAttribute):
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


_PathListPropertyBase = BaseProperty[
  list[Path],
  t.Union[PathLike, PathProperty, Sequence[t.Union[PathLike, PathProperty]]]
]


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
  def _unpack_nested_properties(value: object, references: list[BaseProperty]) -> object:
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

  @staticmethod
  @beartype
  def extract(value: t.Union[PathProperty, 'PathListProperty']) -> list[Path]:
    if isinstance(value, PathProperty):
      return [value.get()]
    elif isinstance(value, PathListProperty):
      return value.get()
    else:
      assert False
