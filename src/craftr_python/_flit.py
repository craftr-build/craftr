
from typing import Any
from craftr.core.properties import Configurable, Property
from ._python import python_project_extensions, _PyprojectUpdater


class FlitBuilder(_PyprojectUpdater, Configurable):
  """
  Injects Flit configuration values into the pyproject file.
  """

  version = Property[str](default='3.2')
  dynamic = Property[list[str]](default=['version', 'description'])

  def update_pyproject_config(self, config: dict[str, Any]) -> None:
    if not self.enabled.get():
      return
    config['build-system'] = {
      'requires': [f'flit_core >={self.version.get()}'],
      'build-backend': 'flit_core.buildapi',
    }
    config.setdefault('project', {})['dynamic'] = self.dynamic.get()


python_project_extensions.register('flit', lambda _: FlitBuilder())
