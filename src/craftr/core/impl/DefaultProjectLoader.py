
"""
Implements the default project loader which loads `build.craftr.py` files and executes them as a
plain Python script providing the current #Project in the global scope.
"""

import typing as t
from pathlib import Path

from craftr.core.base import ProjectLoader
from craftr.core.context import Context
from craftr.core.exceptions import UnableToLoadProjectError
from craftr.core.project import Project

BUILD_SCRIPT_FILENAME = Path('build.craftr.py')


class DefaultProjectLoader(ProjectLoader):

  def __repr__(self) -> str:
    return f'{type(self).__name__}()'

  def load_project(self, context: 'Context', parent: t.Optional[Project], path: Path) -> Project:
    if (filename := path / BUILD_SCRIPT_FILENAME).exists():
      project = Project(context, parent, path)
      context.initialize_project(project)
      scope = {'project': project, '__file__': str(filename), '__name__': '__main__'}
      exec(compile(filename.read_text(), str(filename), 'exec'), scope, scope)
      return project
    raise UnableToLoadProjectError(self, context, parent, path)
