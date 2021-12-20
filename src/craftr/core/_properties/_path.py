
import typing as t
from pathlib import Path
from ._base import Property


class PathProperty(Property[Path]):
  """
  A special property type for paths.
  """

  _base_type = Path


class PathListProperty(Property[list[Path]]):
  """
  A special property type for a list of paths.
  """

  _base_type = list[Path]
