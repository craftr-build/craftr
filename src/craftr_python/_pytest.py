
from typing import Any
from craftr.core.properties import HasProperties, Property
from ._python import python_project_extension, PythonProject


class PytestBuilder(HasProperties):

  def _update_pyproject(self, config: dict[str, Any]) -> None:
    pass


@python_project_extension('pytest')
def _pytest_plugin(project: PythonProject) -> PytestBuilder:
  builder = PytestBuilder()
  project.update_pyproject(builder._update_pyproject)
  return builder
