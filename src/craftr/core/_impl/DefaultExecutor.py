

import typing as t

from termcolor import colored

from .._execute import BuildGraph, Executor
from .._settings import LoadableFromSettings, Settings
from .._tasks import ActionContext, Task

if t.TYPE_CHECKING:
  from .._context import Context


class DefaultExecutor(Executor, LoadableFromSettings):

  def __init__(self, verbose: bool = False) -> None:
    self._verbose = verbose

  @classmethod
  def from_settings(cls, settings: 'Settings') -> 'DefaultExecutor':
    return cls(settings.get_bool('core.verbose', False))

  def execute(self, context: 'Context', graph: BuildGraph) -> None:
    outdated_tasks: set[Task] = set()
    action_context = ActionContext(verbose=self._verbose)
    for task in graph.execution_order():
      if task.always_outdated or task.is_outdated() or any(x in outdated_tasks for x in task.dependencies):
        outdated_tasks.add(task)
        print('> Task', task.path, flush=True)
        # TODO (@nrosenstein): Teardown/cleanup
        for action in (task.actions.pre_run + task.actions.main + task.actions.post_run):
          action.execute(action_context)
        task.on_completed()
      else:
        print('> Task', task.path, colored('UP TO DATE', 'green'), flush=True)
