

import dataclasses
from collections.abc import Callable
from pathlib import Path
from typing import Any, List, Optional, Protocol, Union, runtime_checkable

import toml

from craftr.bld.renderers import FileRenderer
from craftr.core import BoolProperty, Configurable, Extension, ExtensionRegistry, PathProperty, Project, Property
from craftr.utils.weakproperty import WeakProperty

from ._model import Author, Requirement
from ._utils import get_readme_file

python_project_extensions = ExtensionRegistry['PythonProject']()


@runtime_checkable
class _PyprojectUpdater(Protocol):
  def update_pyproject_config(self, config: dict[str, Any]) -> None:
    ...


class PythonProject(Extension[Project]):

  name: Property[str]
  version: Property[str]
  authors: Property[list[Author]] = Property(default=[])
  description: Property[str]
  module_name: Property[str]
  readme: PathProperty
  source: PathProperty = PathProperty(default='src')
  urls: Property[dict[str, str]] = Property(default={})
  typed: BoolProperty
  entry_points: Property[dict[str, dict[str, str]]] = Property(default={})

  def __init__(self, project: Project) -> None:
    super().__init__(project)
    assert not self.enabled.is_static
    self.requirements = PythonRequirements()
    python_project_extensions.apply(self, self)

  @property
  def project(self) -> Project:
    return self.ext_parent

  def author(self, name: str, email: str) -> None:
    self.authors.get().append(Author(name, email))

  def script(self, entrypoint: str, gui: bool = False) -> None:
    key, value = entrypoint.split('=')
    self.entry_points.get().setdefault('gui_scripts' if gui else 'console_scripts', {})[key.strip()] = value.strip()

  def url(self, Source: Optional[str] = None, **kwargs: str) -> None:
    if Source is not None:
      kwargs['Source'] = Source
    self.urls.get().update(kwargs)

  def _update_pyproject(self, config: dict[str, Any]) -> None:
    project = config.setdefault('project', {})

    if version := self.version.get(None):
      project['version'] = version
    project['name'] = self.module_name.get(self.name.get())
    project['authors'] = [x.to_json() for x in self.authors.get()]
    project['urls'] = self.urls.get()

    if desc := self.description.get(None):
      project['description'] = desc
    if project['name'] != self.name.get():
      config.setdefault('metadata', {})['dist-name'] = self.name.get()

    readme = self.readme.get(get_readme_file(str(self.project.directory)))
    if readme:
      project['readme'] = str(Path(readme).relative_to(self.project.directory))

    project['scripts'] = self.entry_points.get().get('console_scripts', {})
    for group, entry_points in self.entry_points.get().items():
      if group != 'console_scripts':
        project.setdefault('entry-points', {})[group] = entry_points

    if self.requirements._python:
      project['requires-python'] = self.requirements._python.version.to_setuptools()
    project['dependencies'] = [r.to_setuptools() for r in self.requirements._run]
    project.setdefault('optional-dependencies', {})['test'] = [r.to_setuptools() for r in self.requirements._test]

    for value in vars(self.ext).values():
      if isinstance(value, _PyprojectUpdater):
        value.update_pyproject_config(config)

  def finalize(self) -> None:
    if not self.enabled.get():
      return
    update_pyproject_task = self.project.task('updatePyproject', UpdatePyprojectTask)
    update_pyproject_task.output_file.set(self.project.directory / 'pyproject.toml')
    update_pyproject_task.updater = self._update_pyproject
    super().finalize()


@dataclasses.dataclass
class PythonRequirements(Configurable):

  _python: Optional[Requirement] = None
  _run: List[Requirement] = dataclasses.field(default_factory=list)
  _test: List[Requirement] = dataclasses.field(default_factory=list)

  def run(self, req: Union[str, Requirement]) -> None:
    req = Requirement.parse(req) if isinstance(req, str) else req
    if req.package == 'python':
      self._python = req
    else:
      self._run.append(req)

  def test(self, req: str) -> None:
    self._test.append(Requirement(req))


class UpdatePyprojectTask(FileRenderer):

  updater: Optional[Callable[[dict[str, Any]], None]] = None

  def _load_pyproject(self) -> dict[str, Any]:
    path = self.output_file.get()
    if path.exists():
      return dict(toml.loads(path.read_text()))
    else:
      return {}

  def get_file_contents(self) -> str:
    config: dict[str, Any] = {}
    assert self.updater is not None
    self.updater(config)
    return toml.dumps(config)
