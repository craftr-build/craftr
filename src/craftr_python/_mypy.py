
from typing import Any
import toml
import requests
from pkg_resources import resource_string
from craftr.bld.system import SystemAction
from craftr.core import Extension
from craftr.core.properties import Property
from ._base import DefaultPythonExtension
from ._python import python_project_extensions


@python_project_extensions.register('mypy')
class Mypy(DefaultPythonExtension):

  _profile_directory = '_mypy_profiles'

  def update_config_from_profile(self, profile_name: str, profile: dict[str, Any]) -> None:
    if 'mypy' in profile:
      config = profile['mypy']
    elif 'tool' in profile and 'mypy' in profile['tool']:
      config = profile['tool']['mypy']
    else:
      raise ValueError(f'unable to detect Mypy configuration in {profile_name!r}')
    self.config.get().update(config)

  def update_pyproject_config(self, config: dict[str, Any]) -> None:
    if not self.enabled.get():
      return
    config.setdefault('tool', {})['mypy'] = self.config.get()

  def plugin(self, plugin: str) -> None:
    """
    Appends a Mypy plugin to the configuration.
    """

    config = self.config.get()
    config.setdefault('plugins', []).append(plugin)

  def finalize(self) -> None:
    if not self.enabled.get():
      return
    super().finalize()
    task = self.ext_parent.project.task('mypy')
    task.group = 'check'
    task.do_last(SystemAction(command=['mypy', self.ext_parent.source.get()], cwd=self.ext_parent.project.directory))
    task.depends_on('updatePyproject')
