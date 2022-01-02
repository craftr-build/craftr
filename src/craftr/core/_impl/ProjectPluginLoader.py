
from .._plugins import PluginLoader, Plugin, PluginNotFoundError


class ProjectPluginLoader(PluginLoader):

  def load_plugin(self, name: str) -> 'Plugin':
    if not (name.startswith('./') or name.startswith('../')):
      raise PluginNotFoundError(self, name)
    raise NotImplementedError(name)
