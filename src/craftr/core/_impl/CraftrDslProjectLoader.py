
import typing as t
from pathlib import Path
from craftr.dsl import ChainContext, Context as _DslContext, Closure, ObjectContext
from .._project import Project, ProjectLoader, UnableToLoadProjectError

if t.TYPE_CHECKING:
  from .._context import Context

BUILD_SCRIPT_FILENAME = 'build.craftr'


def context_factory(obj: t.Any) -> _DslContext:
  if isinstance(obj, Project):
    return ChainContext(ObjectContext(obj), ObjectContext(obj.extensions))
  else:
    return ObjectContext(obj)


class CraftrDslProjectLoader(ProjectLoader):

  def load_project(self, context: 'Context', parent: t.Optional[Project], path: Path) -> Project:
    if (filename := path / BUILD_SCRIPT_FILENAME).exists():
      project = Project(context, parent, path)
      context.init_project(project)
      scope = {'__file__': str(filename), '__name__': project.name}
      Closure(None, None, project, context_factory).run_code(filename.read_text(), str(filename), scope=scope)
      return project

    raise UnableToLoadProjectError(self, context, parent, path)
