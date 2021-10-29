
import dataclasses
import pkg_resources

from craftr.core.base import PluginLoader, Plugin
from craftr.core.exceptions import PluginNotFoundError
from craftr.core.settings import Settings


@dataclasses.dataclass
class DefaultPluginLoader(PluginLoader):
  """
  Default implementation for loading plugins via the `craftr.plugins` entrypoint.
  """

  entrypoint_name: str = 'craftr.plugins'

  @classmethod
  def from_settings(cls, settings: Settings) -> 'DefaultPluginLoader':
    return cls(settings.get('core.plugin.entrypoint', cls.entrypoint_name))

  def load_plugin(self, plugin_name: str) -> Plugin:
    for ep in pkg_resources.iter_entry_points(self.entrypoint_name, plugin_name):
      value = ep.load()
      if not isinstance(value, Plugin):
        raise RuntimeError(f'Plugin "{plugin_name}" loaded by `{self}` does not implement the Plugin protocol.')
      return value
    raise PluginNotFoundError(self, plugin_name)
