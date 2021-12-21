
import abc
import dataclasses
import typing as t
import weakref
from collections.abc import Callable, Collection

from beartype import beartype
from nr.preconditions import check_not_none
from .properties import HasProperties, PathProperty, PathListProperty

_HASHES_KEY = 'tasks.hashes'
_ActionCallable = Callable[['Task', 'ActionContext'], object]
_TaskConfigurator = Callable[['Task'], object]


@dataclasses.dataclass
class ActionContext:
  verbose: bool


class Action(abc.ABC):

  @abc.abstractmethod
  def execute(self, ctx: ActionContext) -> None:
    pass


class LambdaAction(Action):

  def __init__(self, func: Callable[[ActionContext], object]) -> None:
    self._func = func

  def execute(self, ctx: ActionContext) -> None:
    self._func(ctx)


@dataclasses.dataclass
class Actions:
  """
  Holds lists of actions for various purposes.
  """

  main: list[Action] = dataclasses.field(default_factory=list)
  pre_run: list[Action] = dataclasses.field(default_factory=list)
  post_run: list[Action] = dataclasses.field(default_factory=list)
  clean: list[Action] = dataclasses.field(default_factory=list)
  teardown: list[Action] = dataclasses.field(default_factory=list)


class Task(HasProperties):
  """
  The base class for a logical unit of work that is composed of individual actions (see {@link Action}). The
  most common subclass is the {@link DefaultTask}.
  """

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

  #: A list of direct dependencies of this task.
  dependencies: list['Task']

  #: The actions that the task intends to execute.
  actions: Actions

  def __init__(self, project: 'Project', name: str) -> None:
    super().__init__()
    self._project = weakref.ref(project)
    self._name = name
    self._finalized = False
    self.dependencies = []
    self.actions = Actions()
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
    Called from {@link #__init__()}.
    """

  def finalize(self) -> None:
    """
    Called to finalize the state of the task. Raises a {@link RuntimeError} if the task has already been finalized.
    Only after this method is called will the task be considered in a fully initialized and valid state. This method
    should be implemented by subclasses to initialize output properties and populate the {@link #actions}.

    Notes:

    * If the task itself subclasses {@link Action}, this method will automatically add the task itself to
      {@link Actions.main}.

    * Tasks discovered through property references are added to {@link #dependencies} automatically.
    """

    if self._finalized:
      raise RuntimeError('Task already finalized')
    self._finalized = True

    if isinstance(self, Action):
      self.actions.main.append(self)

    for property in self.get_properties().values():
      for ref in property.references:
        if isinstance(ref.owner, Task):
          self.dependencies.append(ref.owner)

    try:
      self.dependencies.remove(self)
    except ValueError:
      pass

  def is_outdated(self) -> bool:
    """
    Check if the task is outdated and needs to be re-run. This does not have to take into account
    {@link #always_outdated}, because the executor can check it separately. Tasks should use the
    {@link Context.metadata_store} to read and write previous information about itself.
    """

    if self.always_outdated:
      return True

    # Find the output properties and check if the files exist.
    missing_output_files = []
    has_output_properties = False
    for property in self.get_properties().values():
      if isinstance(property, (PathProperty, PathListProperty)) and property.is_output:
        has_output_properties = True
        for f in PathListProperty.extract(property):
          if not f.exists():
            missing_output_files.append(f)

    if missing_output_files:
      # TODO (@nrosenstein): Log missing output files
      return True

    if not has_output_properties:
      # A task with no output properties is always outdated; a task that is never outdated doesn't make sense.
      return False

    ctx = self.project.context
    hash_value = ctx.task_hash_calculator.calculate_hash(self)
    stored_hash = ctx.task_hash_store.get(self.path)

    # TODO (@nrosenstein): Log that the hashes are different.
    return hash_value != stored_hash

  def on_completed(self) -> None:
    """
    Called when the task was executed. Updates the task hash.
    """

    if not self.always_outdated:
      ctx = self.project.context
      hash_value = ctx.task_hash_calculator.calculate_hash(self)
      ctx.task_hash_store[self.path] = hash_value

  @beartype
  def depends_on(self, *tasks: t.Union[str, 'Task']) -> None:
    """
    Specify that the task dependends on the specified other tasks. Strings are resolved from the tasks own project.
    """

    for item in tasks:
      if isinstance(item, str):
        self.dependencies += self.project.tasks.resolve(item)
      elif isinstance(item, Task):
        self.dependencies.append(item)

  @beartype
  def do(self, action: t.Union['Action', _ActionCallable]) -> None:
    if callable(action):
      closure = action
      action = LambdaAction(lambda context: closure(self, context))
    self.actions.main.append(action)

  @beartype
  def do_first(self, action: t.Union['Action', _ActionCallable]) -> None:
    if callable(action):
      closure = action
      action = LambdaAction(lambda context: closure(self, context))
    self.actions.pre_run.append(action)

  @beartype
  def do_last(self, action: t.Union['Action', _ActionCallable]) -> None:
    if callable(action):
      closure = action
      action = LambdaAction(lambda context: closure(self, context))
    self.actions.post_run.append(action)

  def __call__(self, closure: _TaskConfigurator) -> 'Task':
    """
    Allows the task to be configured using a closure in Craftr DSL land.
    """

    closure(self)
    return self


class TaskHashCalculator(abc.ABC):

  @abc.abstractmethod
  def calculate_hash(self, task: Task) -> str:
    ...


class TaskSelector(abc.ABC):

  @abc.abstractmethod
  def select_tasks(self, selection: str, project: 'Project') -> Collection[Task]: ...

  @abc.abstractmethod
  def select_default(self, project: 'Project') -> Collection[Task]: ...


TaskSelection =  t.Union[None, str, Task, list[t.Union[str, Task]]]


@beartype
def select_tasks(selector: TaskSelector, project: 'Project', tasks: TaskSelection) -> set[Task]:
  """
  A helper function to select tasks using the given {@link TaskSelector} and a selection of tasks
  that can be either explicit, or strings to expand into existing tasks in the context.
  """

  result = set[Task]()

  if tasks is None:
    result.update(selector.select_default(project))
  else:
    if isinstance(tasks, (str, Task)):
      tasks = t.cast(list[t.Union[str, Task]], [tasks])
    for item in tasks:
      if isinstance(item, Task):
        result.add(item)
      elif isinstance(item, str):
        result_set = selector.select_tasks(item, project)
        if not result_set:
          raise ValueError(f'selector matched no tasks: {item!r}')
        result.update(result_set)

  return result


from ._project import Project  # Can't use TYPE_CHECKING guard because of beartype
