
from craftr.core import Project
from ._python import PythonProject
from . import _mypy, _pytest


def apply(project: Project) -> None:
  project.extensions.python = PythonProject(project)
