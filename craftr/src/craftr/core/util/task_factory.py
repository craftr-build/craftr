
import typing as t
import weakref

from nr.preconditions import check_not_none
from craftr.core.base import Task

if t.TYPE_CHECKING:
  from craftr.core.project import Project

T_Task = t.TypeVar('T_Task', bound=Task)
ConfigureTaskCallback = t.Callable[[T_Task], t.Any]


class TaskFactory(t.Generic[T_Task]):
  """
  This is a helper class that wraps a #Task subclass to act as a factory for that class. It is used
  as a convenience when registering a task as an extension to a #Project such that it can be used
  to define a default task as well as defining a custom named task of the type.
  ```py
  def apply(project: Project, name: str) -> None:
    project.register_extension('myTaskType', TaskFactory(project, 'myTaskType', MyTaskType))
  ```
  Inside a project, the task can then be instantiated in multiple ways:
  ```py
  myTaskType {
    # ...
  }
  assert 'myTaskType' in tasks
  myTaskType 'otherTaskName' {
    # ...
  }
  assert 'otherTaskName' in tasks
  myTaskType name: 'otherTaskName2', configure: {
    # ...
  }
  assert 'otherTaskName2' in tasks
  ```
  """

  def __init__(self, project: 'Project', default_name: str, task_type: t.Type[T_Task]) -> None:
    self._project = weakref.ref(project)
    self._default_name = default_name
    self._task_type = task_type

  def __repr__(self) -> str:
    return f'{type(self).__name__}(project={self._project()}, type={self._task_type})'

  @property
  def project(self) -> 'Project':
    return check_not_none(self._project(), 'lost project reference')

  @property
  def type(self) -> t.Type[T_Task]:
    return self._task_type

  @t.overload
  def __call__(self, configure: ConfigureTaskCallback) -> T_Task: ...

  @t.overload
  def __call__(self, name: str, configure: ConfigureTaskCallback) -> T_Task: ...

  def __call__(
    self,
    name: t.Union[str, ConfigureTaskCallback],
    configure: t.Optional[ConfigureTaskCallback] = None
  ) -> T_Task:
    """
    Create a new instance of the task type.
    """

    if not isinstance(name, str):
      configure = name
      name = None

    project = check_not_none(self._project(), 'lost project reference')
    task = project.task(name or self._default_name, self._task_type)
    configure(task)
    return task
