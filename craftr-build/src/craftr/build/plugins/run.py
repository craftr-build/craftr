
import typing as t

from craftr.build.lib import ExecutableInfo, IExecutableProvider
from craftr.core.base import Action
from craftr.core.impl.actions.CommandAction import CommandAction
from craftr.core.impl.PropertiesTask import PropertiesTask
from craftr.core.project import Project
from craftr.core.property import Property


class RunTask(PropertiesTask):

  executable = Property[t.Union[IExecutableProvider, ExecutableInfo, str]]()

  def init(self) -> None:
    self.default = False
    self.always_outdated = True

  def get_actions(self) -> t.List[Action]:
    executable = self.executable.or_none()
    if isinstance(executable, str):
      executable = ExecutableInfo(executable)
    elif isinstance(executable, IExecutableProvider):
      executable = executable.get_executable_info()
    elif not executable:
      if not self.dependencies:
        raise RuntimeError(f'No dependencies in RunTask')
      providers = t.cast(t.List[IExecutableProvider], list(filter(lambda t: isinstance(t, IExecutableProvider), self.dependencies)))
      if not providers:
        raise RuntimeError(f'No IExecutableProvider in RunTask dependencies')
      if len(providers) > 1:
        raise RuntimeError(f'Multiple IExecutableProvider in RunTask dependencies')
      executable = providers[0].get_executable_info()

    assert isinstance(executable, ExecutableInfo)
    return [CommandAction(executable.invokation_layout or [executable.filename])]


def apply(project: Project) -> None:
  project.extensions.add_task_factory('run', RunTask)
