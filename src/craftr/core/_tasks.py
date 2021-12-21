
import abc
import dataclasses
import hashlib
import typing as t
import weakref
from pathlib import Path

from beartype import beartype
from nr.caching.api import KeyDoesNotExist
from nr.preconditions import check_not_none
from .properties import HasProperties, PathProperty, PathListProperty

if t.TYPE_CHECKING:
  from ._project import Project

_HASHES_KEY = 'tasks.hashes'


@dataclasses.dataclass
class ActionContext:
  verbose: bool


class Action(abc.ABC):

  @abc.abstractmethod
  def execute(self, ctx: ActionContext) -> None:
    pass


class LambdaAction(Action):

  def __init__(self, func: t.Callable[[ActionContext], None]) -> None:
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


class Task(HasProperties, abc.ABC):
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
    hasher = ctx.task_hash_calculator
    hash_value = hasher.calculate_hash(self)

    try:
      stored_hash: t.Optional[str] = ctx.metadata_store.load(_HASHES_KEY, self.path).decode()
    except KeyDoesNotExist:
      stored_hash = None

    # TODO (@nrosenstein): Log that the hashes are different.
    return hash_value != stored_hash

  def on_completed(self) -> None:
    """
    Called when the task was executed. Updates the task hash.
    """

    if not self.always_outdated:
      ctx = self.project.context
      hasher = ctx.task_hash_calculator
      hash_value = hasher.calculate_hash(self).encode()
      self.project.context.metadata_store.store(_HASHES_KEY, self.path, hash_value)

  @beartype
  def depends_on(self, *tasks: t.Union[str, 'Task']) -> None:
    """
    Specify that the task dependends on the specified other tasks. Strings are resolved from the tasks own project.
    """

    for index, item in enumerate(tasks):
      if isinstance(item, str):
        self.dependencies += self.project.tasks.resolve(item)
      elif isinstance(item, Task):
        self.dependencies.append(item)

  @beartype
  def do_first(self, action: t.Union['Action', t.Callable]) -> None:
    if callable(action):
      closure = action
      action = LambdaAction(lambda context: closure(self, context).apply(self))
    self.actions.pre_run.append(action)

  @beartype
  def do_last(self, action: t.Union['Action', t.Callable]) -> None:
    if callable(action):
      closure = action
      action = LambdaAction(lambda context: closure(self, context).apply(self))
    self.actions.post_run.append(action)

  def __call__(self, closure: t.Callable) -> 'Task':
    """
    Allows the task to be configured using a closure in Craftr DSL land.
    """

    closure(self)
    return self


class TaskHashCalculator(abc.ABC):

  @abc.abstractmethod
  def calculate_hash(self, task: Task) -> str:
    ...


class DefaultTaskHashCalculator(TaskHashCalculator):
  """
  Calculates a hash for the task that represents the state of it's inputs (property values and input file contents).
  That hash is used to determine if the task is up to date with it's previous execution or if it needs to be executed.

  > Implementation detail: Expects that all important information of a property value is
  > included in it's #repr(), and that the #repr() is consistent.
  """

  def __init__(self, hash_algo: str = 'sha1') -> None:
    self._hash_algo = hash_algo

  @staticmethod
  def _hash_file(hasher: 'hashlib._Hash', path: Path) -> None:
    with path.open('rb') as fp:
      while True:
        chunk = fp.read(8048)
        hasher.update(chunk)
        if not chunk:
          break

  def calculate_hash(self, task: Task) -> str:
    hasher = hashlib.new(self._hash_algo)
    encoding = 'utf-8'

    for property in sorted(task.get_properties().values(), key=lambda p: p.name):
      hasher.update(property.name.encode(encoding))
      hasher.update(repr(property.or_none()).encode(encoding))

      if isinstance(property, (PathProperty, PathListProperty)) and not property.is_output:
        for f in PathListProperty.extract(property):
          if f.is_file():
            self._hash_file(hasher, f)

    return hasher.hexdigest()
