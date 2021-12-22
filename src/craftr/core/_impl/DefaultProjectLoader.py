
"""
Implements the default project loader which loads `build.craftr.py` files and executes them as a
plain Python script providing the current #Project in the global scope.
"""

from pathlib import Path
from .._project import Project, ProjectLoader, UnableToLoadProjectError

BUILD_SCRIPT_FILENAME = Path('build.craftr.py')


class DefaultProjectLoader(ProjectLoader):

  def __repr__(self) -> str:
    return f'{type(self).__name__}()'

  def load_project(self, project: Project) -> None:
    if not (filename := project.directory / BUILD_SCRIPT_FILENAME).exists():
      raise UnableToLoadProjectError(self, project)
    scope = {'project': project, '__file__': str(filename), '__name__': '__main__'}
    exec(compile(filename.read_text(), str(filename), 'exec'), scope, scope)
