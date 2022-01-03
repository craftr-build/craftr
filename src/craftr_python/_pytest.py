from typing import Any

from craftr.bld.system import SystemAction

from ._base import DefaultPythonExtension
from ._python import python_project_extensions


@python_project_extensions.register('pytest')
class Pytest(DefaultPythonExtension):

  def update_pyproject_config(self, config: dict[str, Any]) -> None:
    pass

  def finalize(self) -> None:
    if not self.enabled.get():
      return
    super().finalize()
    task = self.ext_parent.project.task('pytest')
    task.group = 'check'
    task.do_last(SystemAction(['pytest', self.ext_parent.source.get()], cwd=self.ext_parent.project.directory))
    task.depends_on('updatePyproject')
