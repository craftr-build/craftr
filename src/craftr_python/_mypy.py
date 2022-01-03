
from typing import Any
import toml
import requests
from craftr.core.properties import HasProperties, Property
from ._python import python_project_extension, PythonProject


class MypyBuilder(HasProperties):

  config = Property[dict[str, Any]](default=dict)

  def _update_pyproject(self, config: dict[str, Any]) -> None:
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

    response = requests.get(url)
    response.raise_for_status()
    self.config.get().update(toml.loads(response.text)['mypy'])


@python_project_extension('mypy')
def _mypy_plugin(project: PythonProject) -> MypyBuilder:
  builder = MypyBuilder()
  project.update_pyproject(builder._update_pyproject)
  return builder
