

import abc
import dataclasses
import hashlib
import json
import string
import typing as t
import weakref
from collections.abc import Callable
from pathlib import Path

from nr.preconditions import check_not_none

from craftr.utils.weakproperty import OptionalWeakProperty

from ._extension import Extension

if t.TYPE_CHECKING:
  from ._context import Context
  from ._tasks import Task, _ActionCallable, _TaskConfigurator

T_Task = t.TypeVar('T_Task', bound='Task')


class Project(Extension['Context']):
  """
  A project is a collection of tasks, usually populated through a build script, tied to a directory. Projects
  can have sub projects and there is exactly one root project.
  """

  parent = OptionalWeakProperty['Project'].at('_project', True)

  def __init__(self,
    context: 'Context',
    parent: t.Optional['Project'],
    directory: t.Union[str, Path],
  ) -> None:
    """
    Create a new project. If no *directory* is specified, it will default to the parent directory
    of the caller. If the given *context* does not have a root project defined yet, the project
    will be promoted to the root project.
    """

    super().__init__(context)
    self.parent = parent
    self.directory = Path(directory)
    self._name: t.Optional[str] = None
    self._build_directory: t.Optional[Path] = None
    self._tasks: t.Dict[str, 'Task'] = {}
    self._subprojects: t.Dict[Path, 'Project'] = {}
    self.buildscript = BuildScriptConfig(weakref.ref(self))
    context.init_project(self)

  def __repr__(self) -> str:
    return f'Project("{self.path}")'

  @property
  def context(self) -> 'Context':
    return self.ext_parent

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

    build_directory = self.context.settings.get('core.build_directory', None)
    if build_directory is None:
      return self.directory.joinpath('build')
    else:
      return Path(build_directory)

  @build_directory.setter
  def build_directory(self, path: t.Union[str, Path]) -> None:
    self._build_directory = Path(path)

  @t.overload
  def task(
    self,
    name: str,
    configure: t.Optional['_TaskConfigurator'] = None, /, *,
    do: t.Optional['_ActionCallable'] = None,
  ) -> 'Task': ...

  @t.overload
  def task(
    self,
    name: str,
    task_class: type[T_Task], /,
  ) -> T_Task: ...

  def task(
    self,
    name: str,
    task_class: t.Union[t.Optional['_TaskConfigurator'], type['Task']] = None, /, *,
    do: t.Optional['_ActionCallable'] = None,
  ) -> 'Task':
    """
    Create a new task of type *task_class* (defaulting to #Task) and add it to the project. The
    task name must be unique within the project.
    """

    if name in self._tasks:
      raise ValueError(f'task name already used: {name!r}')

    configure: t.Optional['_TaskConfigurator'] = None
    if task_class is None or not isinstance(task_class, type):
      configure = task_class
      task_class = Task

    task = task_class(self, name)
    self._tasks[name] = task

    if do:
      task.do(do)
    if configure is not None:
      configure(task)

    return task

  @property
  def tasks(self) -> 'ProjectTasks':
    """ Returns the {@link ProjectTasks} object for this project. """

    return ProjectTasks(self, self._tasks)

  def subproject(self, directory: str) -> 'Project':
    """
    Reference a subproject by a path relative to the project directory. If the project has not
    been loaded yet, it will be created and initialized.
    """

    path = (self.directory / directory).resolve()
    if path not in self._subprojects:
      project = Project(self.context, self, path)
      self.context.project_loader.load_project(project)
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
  def subprojects(self) -> list['Project']:
    """ Returns a list of the project's loaded subprojects. """

  @t.overload
  def subprojects(self, closure: Callable[['Project'], None]) -> None:
    """ Call *closure* for every subproject currently loaded in the project.. """

  def subprojects(self, closure = None):
    if closure is None:
      return list(self._subprojects.values())
    else:
      for subproject in self._subprojects.values():
        closure(subproject)

  def apply(self, plugin_name: str) -> None:
    """
    Loads a plugin and applies it to the project. Plugins are loaded via {@link Context#plugin_loader} and applied to the
    project immediately after. When loaded, pugins usually register additional names inin the {@link #extensions}
    namespace object.
    """

    plugin = self.context.plugin_loader.load_plugin(plugin_name)
    plugin.apply(self)

  def finalize(self) -> None:
    super().finalize()
    for task in self.tasks:
      if not task.finalized:
        task.finalize()
    for subproject in self.subprojects():
      subproject.finalize()


class ProjectLoader(abc.ABC):
  """
  Interface for loading/initialize projects from a directory on the filesystem.
  """

  @abc.abstractmethod
  def load_project(self, project: 'Project') -> None: ...


@dataclasses.dataclass
class UnableToLoadProjectError(Exception):
  loader: 'ProjectLoader'
  project: 'Project'


class ProjectTasks:
  """
  Helper class to access tasks in a project.
  """

  def __init__(self, project: 'Project', tasks: t.Dict[str, 'Task']) -> None:
    self._project = weakref.ref(project)
    self._tasks = tasks

  @property
  def project(self) -> 'Project':
    return check_not_none(self._project(), 'lost reference to project')

  def __iter__(self):
    return iter(self._tasks.values())

  def all(self) -> t.Iterator['Task']:
    yield from self.project.tasks
    for subproject in self.project.subprojects():
      yield from subproject.tasks.all()

  def for_each(self, closure: Callable[['Task'], t.Any], all: bool = False) -> None:
    for task in (self.all() if all else self._tasks.values()):
      task(closure)

  def resolve(self, selector: str, raise_empty: bool = True) -> set['Task']:
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


@dataclasses.dataclass
class BuildScriptConfig:
  """
  This class is used to describe metadata in a buildscript, such as Python package dependencies.
  """

  _project: weakref.ReferenceType[Project] = dataclasses.field(repr=False)
  requirements: list[str] = dataclasses.field(default_factory=list)
  index_url: t.Optional[str] = None
  extra_index_urls: list[str] = dataclasses.field(default_factory=list)

  @property
  def project(self) -> Project:
    return check_not_none(self._project(), 'lost reference to project')

  def hash(self) -> str:
    """ Calculates a SHA1 hash for the state of the object. """

    return hashlib.sha1(json.dumps({
      'project': self.project.path,
      'requirements': self.requirements,
      'index_url': self.index_url,
      'extra_index_urls': self.extra_index_urls,
    }).encode('utf8')).hexdigest()

  @t.overload
  def requires(self, package: str, *, version: t.Optional[str] = None) -> None: ...

  @t.overload
  def requires(self, package: str, *packages: str) -> None: ...

  def requires(self, package: str, *packages: str, version: t.Optional[str] = None) -> None:
    for package in (package,) + packages:
      self.requirements.append(f'{package} {version or ""}'.strip())

  def extra_index_url(self, *urls: str) -> None:
    self.extra_index_urls += urls

  def done(self) -> None:
    """
    When not using {@link #__call__()} to configure the build script; call this method to mark that
    the configuration is done.
    """

    self.project.context.buildscript_config_apply(self)

  def __call__(self, configurator: Callable[['BuildScriptConfig'], t.Any]) -> None:
    configurator(self)
    self.done()


class BuildScriptConfigApplier(abc.ABC):
  """
  Interface for applying a buildscript configuration.
  """

  @abc.abstractmethod
  def apply(
    self,
    config: BuildScriptConfig,
    packages_root: Path,
    state: dict[str, t.Any],
    persist: t.Callable[[], None],
  ) -> None:
    """
    Apply the buildscript configuration and install packages into the {@param packages_root}. The method may be called
    multiple times by different projects in the same build.

    @param config: The configuration to apply.
    @param packages_root: The directory where packages should be installed to.
    @param state: A JSON serializable dictionary that can be used to carry state information to the next call.
    @param persist: A function to explicitly persist a state; should only be called before an exception is about
      to be raised as otherwise the mutated {@param state} will be persisted automatically.
    """

  @abc.abstractmethod
  def get_additional_search_paths(self, packages_root: Path) -> list[Path]: ...


from ._tasks import Task
