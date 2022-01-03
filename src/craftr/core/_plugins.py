

import abc
import dataclasses

from ._project import Project


class PluginLoader(abc.ABC):
  """
  Interface for loading and applying plugins by name to a project.
  """

  @abc.abstractmethod
  def load_plugin(self, name: str) -> 'Plugin': ...


class Plugin(abc.ABC):
  """
  Interface for plugins to apply to a project.
  """

  @abc.abstractmethod
  def apply(self, project: Project) -> None: ...


@dataclasses.dataclass
class PluginNotFoundError(Exception):
  loader: PluginLoader
  name: str
