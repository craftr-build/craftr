
"""
A very simple, sequential executor.
"""

import typing as t

from craftr.core.base import Action, ActionContext, GraphExecutor, Task
from craftr.core.graph import Graph
from craftr.core.settings import Settings

try:
  from termcolor import colored
except ImportError:
  def colored(s, *a, **kw):  # type: ignore
    return str(s)


class DefaultTaskGraphExecutor(GraphExecutor['Task']):

  def __init__(self, verbose: bool = False) -> None:
    self._verbose = verbose

  @classmethod
  def from_settings(cls, settings: 'Settings') -> 'DefaultTaskGraphExecutor':
    return cls(settings.get_bool('core.verbose', False))

  def execute(self, graph: Graph[Task]) -> None:
    outdated_tasks: t.Set[Task] = set()
    context = ActionContext(verbose=self._verbose)
    for task in graph.execution_order():
      if task.always_outdated or task.is_outdated() or any(x in outdated_tasks for x in task.get_dependencies()):
        outdated_tasks.add(task)
        print('> Task', task.path, flush=True)
        for action in task.get_action_graph().execution_order():
          action.execute(context)
        task.complete()
      else:
        print('> Task', task.path, colored('UP TO DATE', 'green'), flush=True)
