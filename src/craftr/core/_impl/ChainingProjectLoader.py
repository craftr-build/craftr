

import dataclasses

from beartype import beartype

from .._project import Project, ProjectLoader, UnableToLoadProjectError


@dataclasses.dataclass
class ChainingProjectLoader(ProjectLoader):
  """
  Delegates the project loading process to a sequence of other loaders. Returns the first project loaded by any loader.

  If created from configuration, the `craftr.plugin.loader.delegates` option is respected, which must be a
  comma-separated list of fully qualified lodaer names. A loader name may be trailed by a question mark to ignore
  if the loader name cannot be resolved.
  """

  delegates: list[ProjectLoader]

  def __init__(self, delegates: list[ProjectLoader]) -> None:
    self.delegates = delegates

  def __repr__(self) -> str:
    return f'{type(self).__name__}(delegates={self.delegates!r})'

  @beartype
  def load_project(self, project: Project) -> None:
    for delegate in self.delegates:
      try:
        return delegate.load_project(project)
      except UnableToLoadProjectError as exc:
        if exc.project != project:
          raise
    raise UnableToLoadProjectError(self, project)
