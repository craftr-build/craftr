
from typing import Any
from craftr.core.properties import Configurable
from ._python import python_project_extensions, _PyprojectUpdater


class PytestBuilder(_PyprojectUpdater, Configurable):

  def update_pyproject_config(self, config: dict[str, Any]) -> None:
    if not self.enabled.get():
      return
    pass


python_project_extensions.register('pytest', lambda _: PytestBuilder())
