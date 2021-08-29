
import abc
import enum
import typing as t
import weakref
from dataclasses import dataclass

from nr.preconditions import check_not_none

from craftr.core.configurable import Closure, Configurable
from craftr.core.property.typechecking import Key

if t.TYPE_CHECKING:
  from craftr.core.project import Project
  from craftr.core.task import Task

T_Task = t.TypeVar('T_Task', bound='Task')


class TaskFactory(t.Generic[T_Task]):
  """
  This is a helper class that wraps a #Task subclass to act as a factory for that class. It is used
  as a convenience when registering a task as an extension to a #Project such that it can be used
  to define a default task as well as defining a custom named task of the type.

  ```py
  def apply(project: Project, name: str) -> None:
    project.register_extension('myTaskType', TaskFactoryExtension(project, 'myTaskType', MyTaskType))
  ```

  Inside a project, the task can then be instantiated with a configuration closure, and optionally
  with a custom task name.

  ```py
  myTaskType {
    # ...
  }
  myTaskType('otherTaskName') {
    # ...
  }

  assert 'myTaskType' in tasks
  assert 'otherTaskName' in tasks
  ```
  """

  def __init__(self, project: 'Project', default_name: str, task_type: t.Type[T_Task]) -> None:
    self._project = weakref.ref(project)
    self._default_name = default_name
    self._task_type = task_type

  def __repr__(self) -> str:
    return f'TaskFactoryExtension(project={self._project()}, type={self._task_type})'

  @property
  def project(self) -> 'Project':
    return check_not_none(self._project(), 'lost project reference')

  @property
  def type(self) -> t.Type[T_Task]:
    return self._task_type

  def __call__(self, arg: t.Union[str, Closure]) -> T_Task:
    """
    Create a new instance of the task type. If a string is specified, it will be used as the task
    name. If a closure is specified, the default task name will be used and the task will be
    configured with the closure.
    """

    project = check_not_none(self._project(), 'lost project reference')
    if isinstance(arg, str):
      task = project.task(arg or self._default_name, self._task_type)
    else:
      task = project.task(self._default_name, self._task_type)
      task(arg)
    return task


class Namespace(Configurable):
  """
  Represents a namespace that is directly associated with a project. Plugins register members to
  the namespace with the #add() method or #TaskFactory#s with the #add_task_factory() method.
  """

  class Type(enum.Enum):
    PROJECT_EXT = 'ext'
    PROJECT_EXPORTS = 'exports'
    PLUGIN = 'plugin'

  def __init__(self, project: 'Project', name: str, type: Type) -> None:
    self.__project = weakref.ref(project)
    self.__name__ = name
    self.__type__ = type
    self.__attrs__: t.Dict[str, t.Any] = {}

  def __repr__(self) -> str:
    project = check_not_none(self.__project(), 'lost reference to project')
    if self.__type__ == Namespace.Type.PLUGIN:
      return f'Namespace({self.__type__.value}: {self.__name__!r}, for project: {project.path!r})'
    else:
      return f'Namespace({self.__type__.value}: {project.path!r})'

  def __call__(self, closure: Closure['Namespace', t.Any]) -> None:
    closure(self)

  def __getattr__(self, name: str) -> t.Any:
    try:
      return self.__attrs__[name]
    except KeyError:
      raise AttributeError(f'{self!r} has no attribute {name!r}')

  def add(self, name: str, value: t.Any) -> None:
    if name in self.__attrs__:
      raise RuntimeError(f'{name!r} already registered in {self!r}')
    self.__attrs__[name] = value

  def add_task_factory(self, name: str, task_type: t.Type['Task'], default_task_name: t.Optional[str] = None) -> None:
    project = check_not_none(self.__project(), 'lost reference to project')
    self.add(name, TaskFactory(project, default_task_name or name, task_type))

  def merge_into(self, other: 'Namespace') -> None:
    for key, value in self.__attrs__.items():
      other.add(key, value)


@dataclass
class PluginNotFoundError(Exception):
  loader: t.Optional['IPluginLoader']
  plugin_name : str

  def __str__(self) -> str:
    return f'Plugin "{self.plugin_name}" could not be found' + (
        f' by loader `{self.loader}`' if self.loader else '')


@t.runtime_checkable
class IPlugin(t.Protocol, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def apply(self, project: 'Project', namespace: Namespace) -> t.Any:
    """
    Apply the plugin to the given project and register members to the given *namespace*.
    """


@t.runtime_checkable
class IPluginLoader(t.Protocol, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def load_plugin(self, plugin_name: str) -> IPlugin:
    """
    Load the given plugin by name.
    """
