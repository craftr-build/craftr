
import typing as t
from craftr.dsl import ChainContext, Context, Closure, ObjectContext
from .._project import Project, ProjectLoader, UnableToLoadProjectError


BUILD_SCRIPT_FILENAME = 'build.craftr'


def context_factory(obj: t.Any) -> Context:
  if isinstance(obj, Project):
    return ChainContext(ObjectContext(obj), ObjectContext(obj.extensions))
  else:
    return ObjectContext(obj)


class CraftrDslProjectLoader(ProjectLoader):

  def load_project(self, project: 'Project') -> None:
    if not (filename := project.directory / BUILD_SCRIPT_FILENAME).exists():
      raise UnableToLoadProjectError(self, project)
    scope = {'__file__': str(filename), '__name__': project.name}
    Closure(None, None, project, context_factory).run_code(filename.read_text(), str(filename), scope=scope)
