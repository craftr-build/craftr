from typing import Any

from craftr.bld.system import SystemAction

from ._base import DefaultPythonExtension
from ._python import python_project_extensions
from ._style import Style


@python_project_extensions.register('isort')
class Isort(DefaultPythonExtension):

  _profile_directory = '_isort_profiles'

  def update_config_from_profile(self, profile_name: str, profile: dict[str, Any]) -> None:
    self.config.get().update(profile['isort'] if 'isort' in profile else profile['tool']['isort'])

  def update_pyproject_config(self, config: dict[str, Any]) -> None:
    if not self.enabled.get():
      return
    config.setdefault('tool', {})['isort'] = self.config.get()

  def finalize(self) -> None:
    if not self.enabled.get():
      return
    super().finalize()

    # Inherit style details.
    style: Style = self.ext_parent.ext.style
    config = self.config.get()
    if 'indent' not in config:
      config['indent'] = style.indent.get()
    if 'line_length' not in config:
      config['line_length'] = style.line_length.get()

    task = self.ext_parent.project.task('isort')
    task.do_last(SystemAction(command=['isort', self.ext_parent.source.get()], cwd=self.ext_parent.project.directory))
    task.depends_on('updatePyproject')
