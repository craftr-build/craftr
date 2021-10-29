
import abc
import typing as t
import weakref

from nr.preconditions import check_instance_of, check_not_none

from craftr.core.base import Action, ActionContext, Task
from craftr.core.graph import Graph
from craftr.core.impl.actions.LambdaAction import LambdaAction
from craftr.core.impl.actions.NoopAction import NoopAction
from craftr.core.project import Project

TaskDoCallback = t.Callable[['DefaultTask', ActionContext], None]


class DefaultTask(Task):
  """
  A base class that provides some standard functionality that is commonly useful for tasks.
  """

  def __init__(self, project: 'Project', name: str) -> None:
    self.dependencies = []
    self._project = weakref.ref(project)
    self.name = name
    self.group = None
    self.default = True
    self.description = None
    self.finalized = False
    self.always_outdated = False
    self._do_first_actions: t.List['Action'] = []
    self._do_last_actions: t.List['Action'] = []
    self.init()

  def __repr__(self) -> str:
    return f'{type(self).__name__}({self.path!r})'

  @property
  def project(self) -> 'Project':
    return check_not_none(self._project(), 'lost reference to project')

  @property
  def path(self) -> str:
    return f'{self.project.path}:{self.name}'

  def init(self) -> None:
    """
    Called from #__init__().
    """

  def depends_on(self, *tasks: t.Union[str, Task]) -> None:
    """
    Specify that the task dependends on the specified other tasks. Strings are resolved from the tasks own project.
    """

    if self.finalized:
      raise RuntimeError(f'Task is finalized, cannot add dependency')

    for index, item in enumerate(tasks):
      check_instance_of(item, (str, Task), lambda: 'task ' + str(index))
      if isinstance(item, str):
        self.dependencies += self.project.tasks.resolve(item)
      elif isinstance(item, Task):
        self.dependencies.append(item)

  def do_first(self, action: t.Union[Action, TaskDoCallback]) -> None:
    if callable(action):
      callback = action
      action = LambdaAction(lambda context: callback(self, context))
    if self._do_first_actions:
      action.depends_on(self._do_first_actions[-1])
    self._do_first_actions.append(action)

  def do_last(self, action: t.Union[Action, TaskDoCallback]) -> None:
    if callable(action):
      callback = action
      action = LambdaAction(lambda context: callback(self, context))
    if self._do_last_actions:
      action.depends_on(self._do_last_actions[-1])
    self._do_last_actions.append(action)

  def get_actions(self, graph: Graph[Action]) -> None:
    pass

  # Task

  def finalize(self) -> None:
    """
    Called to finalize the state of the task. Raises a #RuntimeError if the task has already been finalized.
    """

    if self.finalized:
      raise RuntimeError('Task already finalized')
    self.finalized = True

  def get_action_graph(self) -> Graph[Action]:
    temp_graph = Graph[Action]()
    self.get_actions(temp_graph)

    first = NoopAction()
    first.depends_on(*self._do_first_actions)

    custom = NoopAction()
    custom.depends_on(first, *temp_graph.nodes())

    last = NoopAction()
    last.depends_on(custom, *self._do_last_actions)

    return Graph([last])
