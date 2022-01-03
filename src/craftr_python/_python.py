
import dataclasses
import types
import weakref
from collections.abc import Callable
from typing import Any, Optional

import toml
from pkg_resources import iter_entry_points
from craftr.core import Action, Project, Task
from craftr.core.properties import BoolProperty, Property, HasProperties, PathProperty
from craftr.utils.weakproperty import WeakProperty

from ._model import Author

PyprojectUpdater = Callable[[dict[str, Any]], Any]
PythonProjectExtension = Callable[['PythonProject'], Any]
_python_project_extensions: dict[str, PythonProjectExtension] = {}


def python_project_extension(name: str) -> Callable[[PythonProjectExtension], PythonProjectExtension]:
  assert name not in _python_project_extensions, name
  def _decorator(func: PythonProjectExtension) -> PythonProjectExtension:
    assert name not in _python_project_extensions, name
    _python_project_extensions[name] = func
    return func
  return _decorator


class PythonProject(HasProperties):

  name: Property[str]
  version: Property[str]
  authors: Property[list[Author]] = Property(default=[])
  urls: Property[dict[str, str]] = Property(default={})
  typed: BoolProperty
  entry_points: Property[dict[str, dict[str, str]]] = Property(default={})

  def __init__(self, project: Project) -> None:
    super().__init__()
    self._ext = types.SimpleNamespace()
    self._pyproject_updaters: list[PyprojectUpdater] = []
    self.project = project
    self.requirements = PythonRequirements()
    project.on_finalize(self._finalize)
    self.update_pyproject(self._update_pyproject)
    for name, maker in _python_project_extensions.items():
      setattr(self._ext, name, maker(self))
    print(vars(self._ext))

  def __getattr__(self, name: str) -> Any:
    return getattr(self._ext, name)

  project = WeakProperty[Project]('_project', once=True)

  def author(self, name: str, email: str) -> None:
    self.authors.get().append(Author(name, email))

  def script(self, entrypoint: str, gui: bool = False) -> None:
    key, value = entrypoint.split('=')
    self.entry_points.get().setdefault('gui_scripts' if gui else 'console_scripts', {})[key.strip()] = value.strip()

  def url(self, Source: Optional[str] = None, **kwargs: str) -> None:
    if Source is not None:
      kwargs['Source'] = Source
    self.urls.get().update(kwargs)

  def update_pyproject(self, func: PyprojectUpdater) -> None:
    self._pyproject_updaters.append(func)

  def _update_pyproject(self, config: dict[str, Any]) -> None:
    project = config.setdefault('project', {})
    if version := self.version.get(None):
      project['version'] = version
    project['name'] = self.name.get()
    project['authors'] = [x.to_json() for x in self.authors.get()]
    project['urls'] = self.urls.get()
    project['scripts'] = self.entry_points.get().get('console_scripts', {})
    for group, entry_points in self.entry_points.get().items():
      if group != 'console_scripts':
        project.setdefault('entry-points', {})[group] = entry_points

    # TODO (@nrosenstein): Translate to compatible dependency strings
    project['dependencies'] = self.requirements._run
    project.setdefault('optional-dependencies', {})['test'] = self.requirements._test

  def _finalize(self) -> None:
    update_pyproject_task = self.project.task('updatePyproject', UpdatePyprojectTask)
    update_pyproject_task.pyproject_file.set(self.project.directory / 'pyproject.toml')
    update_pyproject_task.pyproject_updaters.set(self._pyproject_updaters)
    print('Finalize!')


@dataclasses.dataclass
class PythonRequirements:

  _run: list[str] = dataclasses.field(default_factory=list)
  _test: list[str] = dataclasses.field(default_factory=list)

  def __call__(self, closure) -> None:
    closure(self)

  def run(self, req: str) -> None:
    self._run.append(req)

  def test(self, req: str) -> None:
    self._test.append(req)


class UpdatePyprojectTask(Action, Task):

  pyproject_file = PathProperty.output()
  pyproject_updaters = Property[list[PyprojectUpdater]](default=[])

  def _load_pyproject(self) -> None:
    path = self.pyproject_file.get()
    if path.exists():
      return toml.loads(path.read_text())
    else:
      return {}

  def _get_updated_pyproject(self) -> None:
    config = self._load_pyproject()
    for updater in self.pyproject_updaters.get():
      updater(config)
    return config

  def is_outdated(self) -> bool:
    return self._load_pyproject() != self._get_updated_pyproject()

  def execute(self, ctx) -> None:
    path = self.pyproject_file.get()
    config = self._get_updated_pyproject()
    path.write_text(toml.dumps(config))
