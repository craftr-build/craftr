
import abc
import enum
import typing as t
import weakref
from pathlib import Path

from nr.caching.api import KeyDoesNotExist
from nr.preconditions import check_instance_of, check_not_none

import craftr
from craftr.core.property import HavingProperties, collect_properties
from craftr.core.configurable import Closure
from craftr.core.util.collections import unique
from .state import calculate_task_hash, unwrap_file_property

if t.TYPE_CHECKING:
  import craftr.core.actions
  from craftr.core.actions import Action
  from craftr.core.project import Project

TASK_HASH_NAMESPACE = 'task-hashes'


class TaskPropertyType(enum.Enum):
  Input = enum.auto()
  InputFile = enum.auto()
  Output = enum.auto()
  OutputFile = enum.auto()


class Task(abc.ABC):
  """
  The raw base class for tasks that represents a logically closed unit of work. It is common to subclass the
  #DefaultTask class instead.
  """

  #: A list of direct dependencies of this task.
  dependencies: t.List['Task']

  #: A list of actions to perform before any other actions in the task.
  do_first_actions: t.List['craftr.core.actions.Action']

  #: A list of actions to perform after any other actions in the task.
  do_last_actions: t.List['craftr.core.actions.Action']

  #: Whether the task should be included if no explicit set of tasks is selected for execution.
  #: This is `True` by default for all tasks (but can be overwritten by subclasses).
  default: bool = True

  #: A short description of the task.
  description: t.Optional[str] = None

  #: A name for the group that the task belongs to. Task groups are used to select tasks via
  #: common identifiers (e.g. `run`, `compile` or `debug` are generic terms that could apply to
  #: a variety of tasks).
  group: t.Optional[str] = None

  #: A boolean flag that indicates whether the task is always to be considered outdated.
  always_outdated: bool = False

  def __init__(self, project: 'Project', name: str) -> None:
    super().__init__()
    self._project = weakref.ref(project)
    self._name = name
    self._finalized = False
    self.dependencies = []
    self.do_first_actions: t.List['Action'] = []
    self.do_last_actions: t.List['Action'] = []
    self.init()

  def __repr__(self) -> str:
    return f'{type(self).__name__}({self.path!r})'

  @property
  def project(self) -> 'Project':
    return check_not_none(self._project(), 'lost reference to project')

  @property
  def name(self) -> str:
    return self._name

  @property
  def path(self) -> str:
    return f'{self.project.path}:{self.name}'

  @property
  def finalized(self) -> bool:
    """ True if #finalize() was called. """

    return self._finalized

  def init(self) -> None:
    """
    Called from #__init__().
    """

  def finalize(self) -> None:
    """
    Called to finalize the state of the task. Raises a #RuntimeError if the task has already been finalized.
    """

    if self._finalized:
      raise RuntimeError('Task already finalized')
    self._finalized = True

  def get_dependencies(self) -> t.List['Task']:
    """
    Return a list of the task's dependencies. This does not not need to include #dependencies as they will be
    taken into account by the executor automatically.
    """

    return []

  def get_actions(self) -> t.List['Action']:
    """
    Return the actions that need to be executed for this task. This does not have to include #do_first_actions
    and #do_last_actions as they will be handled separately by the executor.
    """

    return []

  def is_outdated(self) -> bool:
    """
    Check if the task is outdated and needs to be re-run. This does not have to take into account #always_outdated,
    because the executor can check it separately. The default implementation returns always #True.

    Tasks should use the #Context.metadata_store to read and write previous information about itself.
    """

    return True

  def on_completed(self) -> None:
    """
    Called when the task has finished executing.
    """

  def depends_on(self, *tasks: t.Union[str, 'Task']) -> None:
    """
    Specify that the task dependends on the specified other tasks. Strings are resolved from the tasks own project.
    """

    for index, item in enumerate(tasks):
      check_instance_of(item, (str, Task), lambda: 'task ' + str(index))
      if isinstance(item, str):
        self.dependencies += self.project.tasks.resolve(item)
      elif isinstance(item, Task):
        self.dependencies.append(item)

  def do_first(self, action: t.Union['Action', Closure]) -> None:
    from craftr.core.actions import Action, LambdaAction
    check_instance_of(action, (Action, Closure), 'action')
    if isinstance(action, Closure):
      closure = action
      action = LambdaAction(lambda context: closure(self, context).apply(self))
    self.do_first_actions.append(action)

  def do_last(self, action: t.Union['Action', Closure]) -> None:
    from craftr.core.actions import Action, LambdaAction
    check_instance_of(action, (Action, Closure), 'action')
    if isinstance(action, Closure):
      closure = action
      action = LambdaAction(lambda context: closure(self, context).apply(self))
    self.do_last_actions.append(action)

  def __call__(self, closure: Closure) -> 'Task':
    """
    Allows the task to be configured using a closure in Craftr DSL land.
    """

    closure(self)
    return self


class DefaultTask(Task, HavingProperties):
  """
  This task implementation is what is commonly used to implement custom tasks, as it provides capabilities to
  automatically deduce dependencies between tasks via property relationships (see #HavingProperties). If you
  use the property of one task to set the value of another, that first task becomes a dependency of the latter.

  Furthermore, the type of the property can define how the task's properties are handled in respect to its
  up-to-date calculation. E.g. if a property is marked as a #TaskPropertyType.OutputFile, the task is considered
  out-of-date if the output file does not exist or if any of the task's input files (marked with
  #TaskPropertyType.InputFile) have been changed since the output file was produced.
  """

  Input = TaskPropertyType.Input
  InputFile = TaskPropertyType.InputFile
  Output = TaskPropertyType.Output
  OutputFile = TaskPropertyType.OutputFile

  def finalize(self) -> None:
    """
    Called to finalize the task. This is called automatically after the task is configured.
    Properties are finalized in this call. The subclass gets a chance to set any output properties
    that are derived other properties.
    """

    if self._finalized:
      raise RuntimeError('Task already finalized')
    self._finalized = True
    for prop in self.get_properties().values():
      prop.finalize()

  def get_dependencies(self) -> t.List['Task']:
    """ Get all direct dependencies of the task, including those inherited through properties. """

    dependencies = self.dependencies[:]

    for prop in self.get_properties().values():
      if TaskPropertyType.Output not in prop.annotations:
        dependencies.extend(t.cast(Task, p.origin) for p in collect_properties(prop) if isinstance(p.origin, Task))

    dependencies = list(unique(dependencies))

    try:
      dependencies.remove(self)
    except ValueError:
      pass

    return dependencies

  def is_outdated(self) -> bool:
    """
    Checks if the task is outdated.
    """

    if self.always_outdated:
      return True

    # Check if any of the output file(s) don't exist.
    for prop in self.get_properties().values():
      _is_input, is_output, files = unwrap_file_property(prop)
      if is_output and any(not Path(f).exists() for f in files):
        return True

    # TODO(NiklasRosenstein): If the task has no input file properties or does not produce output
    #   files should always be considered as outdated.

    hash_value = calculate_task_hash(self)

    try:
      stored_hash: t.Optional[str] = self.project.context.metadata_store.\
          namespace(TASK_HASH_NAMESPACE).load(self.path).decode()
    except KeyDoesNotExist:
      stored_hash = None

    return hash_value != stored_hash

  def on_completed(self) -> None:
    """
    Called when the task was executed.
    """

    if not self.always_outdated:
      self.project.context.metadata_store.\
          namespace(TASK_HASH_NAMESPACE).store(self.path, calculate_task_hash(self).encode())
