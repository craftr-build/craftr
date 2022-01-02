
from craftr.core import Project
from ._python import PythonProject


def apply(project: Project) -> None:
  project.extensions.python = PythonProject(project)
