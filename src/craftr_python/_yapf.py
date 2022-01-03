from typing import Any

from craftr.bld.system import SystemAction

from ._base import DefaultPythonExtension
from ._isort import Isort
from ._python import python_project_extensions
from ._style import Style


@python_project_extensions.register('yapf')
class Yapf(DefaultPythonExtension):

  _profile_directory = '_yapf_profiles'

  def update_config_from_profile(self, profile_name: str, profile: dict[str, Any]) -> None:
    self.config.get().update(profile['yapf'] if 'yapf' in profile else profile['tool']['yapf'])

  def update_pyproject_config(self, config: dict[str, Any]) -> None:
    if not self.enabled.get():
      return
    config.setdefault('tool', {})['yapf'] = self.config.get()

  def finalize(self) -> None:
    if not self.enabled.get():
      return
    super().finalize()

    # Inherit style details.
    style: Style = self.ext_parent.ext.style
    config = self.config.get()
    if 'INDENT_WIDTH' not in config:
      config['INDENT_WIDTH'] = len(style.indent.get())
    if 'COLUMN_LIMIT' not in config:
      config['COLUMN_LIMIT'] = style.line_length.get()

    pyproject = self.ext_parent
    project = pyproject.project

    task = self.ext_parent.project.task('yapf')
    task.do_last(
      SystemAction(command=['yapf', '-i', '-r', pyproject.source.get()], cwd=self.ext_parent.project.directory)
    )
    task.depends_on('updatePyproject')

    # NOTE (@nrosenstein): The way isort wraps long import lines may be different from Yapf; to ensure a
    #   consistent result we make Yapf run after isort always.
    isort: Isort = self.ext_parent.ext.isort
    if isort.enabled.get():
      task.depends_on('isort')
