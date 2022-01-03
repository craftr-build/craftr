
from typing import Any
from craftr.core.properties import Configurable, Property
from craftr.utils.weakproperty import WeakProperty
from ._python import python_project_extensions, _PyprojectUpdater, PythonProject


class FlitBuilder(_PyprojectUpdater, Configurable):
  """
  Injects Flit configuration values into the pyproject file.
  """

  version = Property[str](default='3.2')
  pyproject = WeakProperty[PythonProject]('_pyproject', once=True)

  def __init__(self, pyproject: PythonProject) -> None:
    self.pyproject = pyproject

  def update_pyproject_config(self, config: dict[str, Any]) -> None:
    if not self.enabled.get():
      return
    config['build-system'] = {
      'requires': [f'flit_core >={self.version.get()}'],
      'build-backend': 'flit_core.buildapi',
    }

    dynamic = []
    if not self.pyproject.version.is_set():
      dynamic.append('version')
    if not self.pyproject.description.is_set():
      dynamic.append('description')
    if dynamic:
      config.setdefault('project', {})['dynamic'] = dynamic


python_project_extensions.register('flit', FlitBuilder)
