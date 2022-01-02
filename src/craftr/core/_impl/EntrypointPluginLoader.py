
import dataclasses
import pkg_resources
import typing as t
from beartype import beartype
from loguru import logger
from .._plugins import PluginLoader, PluginNotFoundError, Plugin
from .._project import Project


@dataclasses.dataclass
class EntrypointPluginLoader(PluginLoader):
  entrypoint_group: str = 'craftr_plugins'

  @beartype
  def load_plugin(self, name: str) -> 'Plugin':
    eps = list(pkg_resources.iter_entry_points(self.entrypoint_group, name))
    if len(eps) > 1:
      logger.warning('multiple entries for entrypoint {}:{} ({}), using first ({})',
        self.entrypoint_group, name, len(eps), eps[0])
    if not eps:
      raise PluginNotFoundError(self, name)
    logger.debug('loading plugin {} from entrypoint {}', name, eps[0])
    cls = eps[0].load()
    if isinstance(cls, type):
      return cls()
    elif isinstance(cls, Plugin):
      return cls
    elif callable(cls):
      return _FunctionPlugin(cls)
    return cls


@dataclasses.dataclass
class _FunctionPlugin(Plugin):
  _func: t.Callable[[Project], None]

  def apply(self, project: Project) -> None:
    return self._func(project)
