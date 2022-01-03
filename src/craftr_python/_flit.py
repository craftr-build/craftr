
from typing import Any
import toml
import requests
from craftr.core.properties import Configurable, Property
from ._python import python_project_extension, PythonProject


class FlitBuilder(Configurable):
  """
  Injects Flit configuration values into the pyproject file.
  """

  version = Property[str](default='3.2')
  dynamic = Property[list[str]](default=['version', 'description'])

  def _update_pyproject(self, config: dict[str, Any]) -> None:
    if not self.enabled.get():
      return
    config['build-system'] = {
      'requires': [f'flit_core >={self.version.get()}'],
      'build-backend': 'flit_core.buildapi',
    }
    config.setdefault('project', {})['dynamic'] = self.dynamic.get()



@python_project_extension('flit')
def _flit_plugin(project: PythonProject) -> FlitBuilder:
  builder = FlitBuilder()
  project.update_pyproject(builder._update_pyproject)
  return builder
