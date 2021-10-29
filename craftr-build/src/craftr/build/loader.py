
import typing as t
from pathlib import Path
from craftr.dsl.runtime import ChainContext, Context, Closure, ObjectContext, MapContext
from craftr.core.base import ProjectLoader
from craftr.core.context import Context
from craftr.core.project import Project
from craftr.core.exceptions import UnableToLoadProjectError

BUILD_SCRIPT_FILENAME = 'build.craftr'


def context_factory(obj: t.Any) -> Context:
  if isinstance(obj, Project):
    return ChainContext(ObjectContext(obj), MapContext(obj.extensions.__attrs__, 'project extensions'))
  else:
    return ObjectContext(obj)


class DslProjectLoader(ProjectLoader):

  def load_project(self, context: Context, parent: t.Optional[Project], path: Path) -> Project:
    if (filename := path / BUILD_SCRIPT_FILENAME).exists():
      project = Project(context, parent, path)
      context.initialize_project(project)
      scope = {'__file__': str(filename), '__name__': project.name}
      Closure(None, None, project, context_factory).run_code(filename.read_text(), str(filename), scope=scope)
      return project

    raise UnableToLoadProjectError(self, context, parent, path)
