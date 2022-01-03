
from typing import Any
import toml
import requests
from pkg_resources import resource_string
from craftr.bld.system import SystemAction
from craftr.core import Extension
from craftr.core.properties import Property
from ._python import python_project_extensions, PythonProject


@python_project_extensions.register('mypy')
class MypyBuilder(Extension[PythonProject]):

  config = Property[dict[str, Any]](default=dict)
  _load_default_profile = True

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

  def profile(self, profile_name_or_url: str) -> None:
    """
    Loads a TOML configuration that contains a "mypy" or "tool.mypy" section from a built-in profile name or URL.
    """

    self._load_default_profile = False

    if profile_name_or_url.startswith('http'):
      # TODO (@nrosenstein): Cache the response for a certain duration to speed up subsequent invokations?
      response = requests.get(profile_name_or_url)
      response.raise_for_status()
      profile = toml.loads(response.text)
    else:
      profile = toml.loads(resource_string(__name__, f'_mypy_profiles/{profile_name_or_url}.toml').decode('utf8'))

    if 'mypy' in profile:
      config = profile['mypy']
    elif 'tool' in profile and 'mypy' in profile['tool']:
      config = profile['tool']['mypy']
    else:
      raise ValueError(f'unable to detect Mypy configuration in {profile_name_or_url!r}')

    self.config.get().update(config)

  def finalize(self) -> None:
    if not self.enabled.get():
      return
    if self._load_default_profile and self.config.get() == {}:
      self.profile('default')
    task = self.ext_parent.project.task('mypy')
    task.group = 'check'
    task.do_last(SystemAction(command=['mypy', self.ext_parent.source.get()], cwd=self.ext_parent.project.directory))
    task.depends_on('updatePyproject')
