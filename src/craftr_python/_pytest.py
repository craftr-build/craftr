
from typing import Any
from craftr.bld.system import SystemAction
from craftr.core import Extension
from ._python import python_project_extensions, PythonProject


@python_project_extensions.register('pytest')
class PytestBuilder(Extension[PythonProject]):

  def update_pyproject_config(self, config: dict[str, Any]) -> None:
    pass

  def finalize(self) -> None:
    if not self.enabled.get():
      return
    task = self.ext_parent.project.task('pytest')
    task.group = 'check'
    task.do_last(SystemAction(['pytest', self.ext_parent.source.get()], cwd=self.ext_parent.project.directory))
    task.depends_on('updatePyproject')
