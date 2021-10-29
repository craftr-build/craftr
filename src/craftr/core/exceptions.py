
import dataclasses
import typing as t
from pathlib import Path

if t.TYPE_CHECKING:
  from .base import PluginLoader, ProjectLoader
  from .context import Context
  from .project import Project


@dataclasses.dataclass
class PluginNotFoundError(Exception):
  loader: t.Optional['PluginLoader']
  plugin_name : str

  def __str__(self) -> str:
    return f'Plugin "{self.plugin_name}" could not be found' + (f' by loader `{self.loader}`' if self.loader else '')


class BuildError(Exception):
  pass


@dataclasses.dataclass
class UnableToLoadProjectError(Exception):
  loader: 'ProjectLoader'
  context: 'Context'
  parent: t.Optional['Project']
  path: Path


class NoValueError(Exception):
  """ Raised when a provider has no value. """
