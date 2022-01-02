
import dataclasses
import types
from typing import Any, Optional

from craftr.core import Project, Task
from craftr.core.properties import BoolProperty, Property, HasProperties

from ._model import Author
from ._mypy import MypyBuilder
from ._pytest import PytestBuilder


class PythonProject(HasProperties):

  name: Property[str]
  authors: Property[list[Author]] = Property(default=[])
  urls: Property[dict[str, str]] = Property(default={})
  typed: BoolProperty
  scripts: Property[dict[str, list[str]]] = Property(default={})

  def __init__(self, project: Project) -> None:
    super().__init__()
    self._project = project
    self._ext = types.SimpleNamespace()
    self.requirements = PythonRequirements()
    self.mypy = MypyBuilder()
    self.pytest = PytestBuilder()

  def __getattr__(self, name: str) -> Any:
    return getattr(self._ext, name)

  def author(self, name: str, email: str) -> None:
    self.authors.get().append(Author(name, email))

  def script(self, entrypoint: str, gui: bool = False) -> None:
    self.scripts.get().setdefault('gui_scripts' if gui else 'console_scripts', []).append(entrypoint)

  def url(self, Home: Optional[str] = None, **kwargs: str) -> None:
    if Home is not None:
      kwargs['Home'] = Home
    self.urls.get().update(kwargs)


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
