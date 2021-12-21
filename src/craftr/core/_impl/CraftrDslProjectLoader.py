
import typing as t
from pathlib import Path
from craftr.dsl import ChainContext, Context, Closure, ObjectContext, MapContext
from .._project import Project, ProjectLoader, UnableToLoadProjectError

if t.TYPE_CHECKING:
  from .._context import Context

BUILD_SCRIPT_FILENAME = 'build.craftr'


def context_factory(obj: t.Any) -> Context:
  if isinstance(obj, Project):
    return ChainContext(ObjectContext(obj), MapContext(obj.extensions.__attrs__, 'project extensions'))
  else:
    return ObjectContext(obj)


class CraftrDslProjectLoader(ProjectLoader):

  def load_project(self, context: Context, parent: t.Optional[Project], path: Path) -> Project:
    if (filename := path / BUILD_SCRIPT_FILENAME).exists():
      project = Project(context, parent, path)
      context.initialize_project(project)
      scope = {'__file__': str(filename), '__name__': project.name}
      Closure(None, None, project, context_factory).run_code(filename.read_text(), str(filename), scope=scope)
      return project

    raise UnableToLoadProjectError(self, context, parent, path)
