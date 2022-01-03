

import abc
import typing as t
from collections.abc import Collection

from craftr.utils.digraph import DiGraph, remove_with_predecessors, topological_sort

from ._tasks import Task

if t.TYPE_CHECKING:
  from ._context import Context


class BuildGraph(DiGraph[str, Task, None]):

  def __init__(self) -> None:
    super().__init__()

  def add_tasks(self, tasks: Collection[Task], *, seen: t.Optional[set[Task]] = None) -> None:
    if seen is None:
      seen = set()
    for task in set(tasks):
      seen.add(task)
      self.nodes[task.path] = task
      for dep in task.dependencies:
        self.nodes[dep.path] = dep
        self.edges[(dep.path, task.path)] = None
      self.add_tasks(task.dependencies, seen=seen)

  def exclude_tasks(self, tasks: Collection[Task]) -> None:
    remove_with_predecessors(self, [t.path for t in tasks])

  def execution_order(self) -> list[Task]:
    return [self.nodes[k] for k in topological_sort(self)]


class Executor(abc.ABC):

  @abc.abstractmethod
  def execute(self, context: 'Context', graph: BuildGraph) -> None: ...
