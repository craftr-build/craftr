
from typing import Any, ClassVar, Optional
import toml
import requests
from pkg_resources import resource_string
from craftr.core import Extension
from craftr.core.properties import Property
from ._python import PythonProject


class DefaultPythonExtension(Extension[PythonProject]):
  """
  Base class for Python extensions that are configurable from a TOML template.
  """

  _load_default_profile = True
  _profile_directory: ClassVar[Optional[str]] = None
  _profile_default: ClassVar[str] = 'default'

  config = Property[dict[str, Any]](default=dict)

  def update_config_from_profile(self, profile_name: str, profile: dict[str, Any]) -> None:
    raise NotImplementedError

  def update_pyproject_config(self, config: dict[str, Any]) -> None:
    raise NotImplementedError

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
      path = f'{self._profile_directory}/{profile_name_or_url}.toml'
      profile = toml.loads(resource_string(__name__, path).decode('utf8'))

    self.update_config_from_profile(profile_name_or_url, dict(profile))

  def finalize(self) -> None:
    if not self.enabled.get():
      return
    if self._load_default_profile and self.config.get() == {} and self._profile_directory:
      self.profile(self._profile_default)
