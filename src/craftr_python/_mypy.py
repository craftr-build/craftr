
from typing import Any
import toml
import requests
from craftr.core.properties import Configurable, Property
from ._python import python_project_extensions, _PyprojectUpdater


class MypyBuilder(_PyprojectUpdater, Configurable):

  config = Property[dict[str, Any]](default=dict)

  def _update_pyproject(self, config: dict[str, Any]) -> None:
    if not self.enabled.get():
      return
    config['mypy'] = self.config.get()

  def plugin(self, plugin: str) -> None:
    """
    Appends a Mypy plugin to the configuration.
    """

    config = self.config.get()
    config.setdefault('plugins', []).append(plugin)

  def from_(self, url: str) -> None:
    """
    Loads a TOML configuration that contains a "mypy" section from a URL.
    """

    # TODO (@nrosenstein): Cache the response for a certain duration to speed up subsequent invokations?
    response = requests.get(url)
    response.raise_for_status()
    self.config.get().update(toml.loads(response.text)['mypy'])


python_project_extensions.register('mypy', lambda _: MypyBuilder())
