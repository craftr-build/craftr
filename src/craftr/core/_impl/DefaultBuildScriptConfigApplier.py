import subprocess as sp
import sys
import typing as t
from pathlib import Path

from loguru import logger

from .._project import BuildScriptConfig, BuildScriptConfigApplier


class DefaultBuildScriptConfigApplier(BuildScriptConfigApplier):
  """
  Uses Pip to install dependencies.
  """

  def apply(
    self,
    config: BuildScriptConfig,
    packages_dir: Path,
    state: dict[str, t.Any],
    persist: t.Callable[[], None],
  ) -> None:
    previous_state_hash: t.Optional[str] = state.get(config.project.path)
    current_state_hash = config.hash()
    if previous_state_hash == current_state_hash:
      logger.info('skip apply buildscript config for project "{}" (already up to date)', config.project.path)
      return

    # TODO (@nrosenstein): Handle some verbosity flag to pass/not pass '-q'
    # TODO (@nrosenstein): How to enable Pip version constraint checks for packages installed into the packages_dir?
    # TODO (@nrosenstein): Make sure that requirements that have been dropped are removed again?

    command = [sys.executable, '-m', 'pip', 'install', f'--prefix={packages_dir.resolve()}', '-q']
    command += ['--no-python-version-warning', '--disable-pip-version-check']
    if config.index_url:
      command += ['--index-url=' + config.index_url]
    command += ['--extra-index-url=' + u for u in config.extra_index_urls]
    command += config.requirements

    logger.info('applying buildscript config for project "{}"', config.project.path)
    logger.debug(command)
    sp.check_output(command)

    state[config.project.path] = current_state_hash

  def get_additional_search_paths(self, packages_root: Path) -> list[Path]:
    # TODO (@nrosenstein): special handling for Windows?
    return [packages_root / 'lib' / f'python{sys.version[:3]}' / 'site-packages']
