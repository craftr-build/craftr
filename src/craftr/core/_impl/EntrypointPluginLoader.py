
import dataclasses
import pkg_resources
from beartype import beartype
from loguru import logger
from .._plugins import PluginLoader, PluginNotFoundError, Plugin


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
    return cls()
