
from craftr.core import Project


def apply(project: Project) -> None:
  # TODO (@nrosenstein)
  project.extensions.license = lambda n: None
