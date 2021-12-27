
from .._plugins import PluginLoader, Plugin


class ProjectPluginLoader(PluginLoader):

  def load_plugin(self, name: str) -> 'Plugin':
    if not (name.startswith('./') or name.startswith('../')):
      pass
