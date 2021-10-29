
import typing as t
import weakref

from nr.preconditions import check_not_none

from craftr.core.util.task_factory import TaskFactory

if t.TYPE_CHECKING:
  from craftr.core.project import Project


class Namespace:
  """
  Represents a namespace that is directly associated with a project. Plugins register members to
  the namespace with the #add() method or #TaskFactory#s with the #add_task_factory() method.
  """

  def __init__(self, project: 'Project', name: str) -> None:
    self.__project = weakref.ref(project)
    self.__name__ = name
    self.__attrs__: t.Dict[str, t.Any] = {}

  def __repr__(self) -> str:
    project = check_not_none(self.__project(), 'lost reference to project')
    return f'Namespace(project={project.path!r}, name={self.__name__!r})'

  def __call__(self, func: t.Callable[['Namespace'], t.Any]) -> None:
    func(self)

  def __getitem__(self, name: str) -> t.Any:
    try:
      return self.__attrs__[name]
    except KeyError:
      raise AttributeError(f'{self!r} has no attribute {name!r}')

  def __contains__(self, name: str) -> bool:
    return name in self.__attrs__

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
