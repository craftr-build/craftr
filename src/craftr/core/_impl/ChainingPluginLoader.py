
import dataclasses
from beartype import beartype
from .._plugins import PluginLoader, PluginNotFoundError, Plugin


@dataclasses.dataclass
class ChainingPluginLoader(PluginLoader):
  delegates: list[PluginLoader]

  @beartype
  def load_plugin(self, name: str) -> 'Plugin':
    for delegate in self.delegates:
      try:
        return delegate.load_plugin(name)
      except PluginNotFoundError as exc:
        if exc.name != name:
          raise
    raise PluginNotFoundError(self, name)
