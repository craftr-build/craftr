
import glob
import string
import sys
import typing as t
import weakref
from pathlib import Path

from nr.preconditions import check_instance_of, check_not_none
from craftr.core.configurable import Closure
from craftr.core.plugin.api import Namespace
from craftr.core.util.weak import WeakInstanceMethod

if t.TYPE_CHECKING:
  from craftr.core.task import Task
  from craftr.core.context import Context

T_Task = t.TypeVar('T_Task', bound='Task')


class Project:
  """
  A project is a collection of tasks, usually populated through a build script, tied to a
  directory. Projects can have sub projects and there is usually only one root project in
  build.
  """

  def __init__(self,
    context: 'Context',
    parent: t.Optional['Project'] = None,
    directory: t.Union[None, str, Path] = None,
  ) -> None:
    """
    Create a new project. If no *directory* is specified, it will default to the parent directory
    of the caller. If the given *context* does not have a root project defined yet, the project
    will be promoted to the root project.
    """

    if directory is None:
      directory = Path(sys._getframe(1).f_code.co_filename).parent

    self._context = weakref.ref(context)
    self._parent = weakref.ref(parent) if parent is not None else parent
    self.directory = Path(directory)
    self._name: t.Optional[str] = None
    self._build_directory: t.Optional[Path] = None
    self._tasks: t.Dict[str, 'Task'] = {}
    self._subprojects: t.Dict[Path, 'Project'] = {}
    self._on_apply: t.Optional[Closure] = None
    self.ext = Namespace(self, self.path, Namespace.Type.PROJECT_EXT)
    self.exports = Namespace(self, self.path, Namespace.Type.PROJECT_EXPORTS)

    self.ext.add('project', weakref.proxy(self))
    self.ext.add('apply', WeakInstanceMethod(self.apply))
    self.ext.add('exports', self.exports)

    if not context._root_project:
      context._root_project = self

  def __repr__(self) -> str:
    return f'Project("{self.path}")'

  @property
  def context(self) -> 'Context':
    return check_not_none(self._context(), 'lost reference to context')

  @property
  def parent(self) -> t.Optional['Project']:
    if self._parent is not None:
      return check_not_none(self._parent(), 'lost reference to parent')
    return None

  @property
  def name(self) -> str:
    if self._name is not None:
      return self._name
    return self.directory.name

  @name.setter
  def name(self, name: str) -> None:
    if set(name) - set(string.ascii_letters + string.digits + '_-'):
      raise ValueError(f'invalid task name: {name!r}')
    self._name = name

  @property
  def path(self) -> str:
    parent = self.parent
    if parent is None:
      return self.name
    return f'{parent.path}:{self.name}'

  @property
  def build_directory(self) -> Path:
    if self._build_directory:
      return self._build_directory
    return self.context.get_default_build_directory(self)

  @build_directory.setter
  def build_directory(self, path: t.Union[str, Path]) -> None:
    self._build_directory = Path(path)

  @t.overload
  def task(self, name: str) -> 'Task': ...

  @t.overload
  def task(self, name: str, task_class: t.Type[T_Task]) -> T_Task: ...

  def task(self, name: str, task_class: t.Optional[t.Type[T_Task]] = None) -> T_Task:
    """
    Create a new task of type *task_class* (defaulting to #Task) and add it to the project. The
    task name must be unique within the project.
    """

    if name in self._tasks:
      raise ValueError(f'task name already used: {name!r}')

    from craftr.core.task import Task
    task = (task_class or Task)(self, name)
    self._tasks[name] = task
    return t.cast(T_Task, task)

  @property
  def tasks(self) -> 'TaskContainer':
    """ Returns the #TaskContainer object for this project. """

    return TaskContainer(self, self._tasks)

  def subproject(self, directory: str) -> 'Project':
    """
    Reference a subproject by a path relative to the project directory. If the project has not
    been loaded yet, it will be created and initialized.
    """

    path = (self.directory / directory).resolve()
    if path not in self._subprojects:
      project = self.context.project_loader.load_project(self.context, self, path)
      self._subprojects[path] = project
    return self._subprojects[path]

  def get_subproject_by_name(self, name: str) -> 'Project':
    """
    Returns a sub project of this project by it's name. Raises a #ValueError if no sub project
    with the specified name exists in the project.
    """

    for project in self._subprojects.values():
      if project.name == name:
        return project

    raise ValueError(f'project {self.path}:{name} does not exist')

  @t.overload
  def subprojects(self) -> t.List['Project']:
    """ Returns a list of the project's loaded subprojects. """

  @t.overload
  def subprojects(self, closure: t.Callable[['Project'], None]) -> None:
    """ Call *closure* for every subproject currently loaded in the project.. """

  def subprojects(self, closure = None):
    if closure is None:
      return list(self._subprojects.values())
    else:
      for subproject in self._subprojects.values():
        closure(subproject)

  def on_apply(self, func: Closure) -> None:
    """
    Register a function to call when the project is applied using `apply from_project: <project>`.
    """

    if self._on_apply is not None:
      raise RuntimeError(f'{self}.on_apply() already set')
    self._on_apply = func

  def apply(
    self,
    plugin_name: t.Optional[str] = None,
    from_project: t.Union[None, str, 'Project'] = None,
    merge: bool = True,
  ) -> Namespace:
    """
    Loads a plugin and applies it to the project. Plugins are loaded via #Context.plugin_loader and applied to the
    project immediately after. The default implementation for loading plugins uses Python package entrypoints
    as configured in the #Context.

    Returns the extension namespace created for the plugin. The extension is also merged into the #Project.ext
    namespace unless the *merge* parameter is set to #False.
    """

    if plugin_name is not None:
      if from_project is not None:
        raise TypeError('plugin_name and from_project should not be specified at the same time')
      check_instance_of(plugin_name, str, 'plugin_name')
      plugin = self.context.plugin_loader.load_plugin(plugin_name)
      namespace = Namespace(self, plugin_name, Namespace.Type.PLUGIN)
      plugin.apply(self, namespace)

    elif from_project is not None:
      from_project = self.subproject(from_project) if isinstance(from_project, str) else from_project
      check_instance_of(from_project, (str, Project), 'from_project')
      if not from_project._on_apply:
        raise ValueError(f'{from_project} has no on_apply handler')
      from_project._on_apply(self)
      namespace = from_project.exports

    else:
      raise TypeError('need plugin_name or from_project')

    if merge:
      namespace.merge_into(self.ext)

    return namespace

  def file(self, sub_path: str) -> Path:
    return self.directory / sub_path

  def glob(self, pattern: str) -> t.List[Path]:
    """
    Apply the specified glob pattern relative to the project directory and return a list of the
    matched files.
    """

    return [Path(f) for f in glob.glob(str(self.directory / pattern))]

  def finalize(self) -> None:
    for task in self.tasks:
      if not task.finalized:
        task.finalize()
    for project in self.subprojects():
      project.finalize()


class TaskContainer:

  def __init__(self, project: 'Project', tasks: t.Dict[str, 'Task']) -> None:
    self._project = weakref.ref(project)
    self._tasks = tasks

  @property
  def project(self) -> 'Project':
    return check_not_none(self._project(), 'lost reference to project')

  def __iter__(self):
    return iter(self._tasks.values())

  def for_each(self, closure: 'Closure') -> None:
    for task in self._tasks.values():
      task(closure)

  def resolve(self, selector: str, raise_empty: bool = True) -> t.Set['Task']:
    tasks = self.project.context.task_selector.select_tasks(selector, self.project)
    if not tasks and raise_empty:
      raise ValueError(f'no task matched selector {selector!r} in project {self.project}')
    return set(tasks)

  def __getattr__(self, key: str) -> 'Task':
    try:
      return self[key]
    except KeyError:
      raise AttributeError(key)

  def __getitem__(self, key: str) -> 'Task':
    return self._tasks[key]


def all_tasks(project: Project) -> t.Iterator['Task']:
  yield from project.tasks
  for subproject in project.subprojects():
    yield from all_tasks(subproject)
