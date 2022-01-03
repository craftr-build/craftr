import typing as t

from craftr.dsl import ChainContext, Closure, Context, ObjectContext

from .._project import Extension, Project, ProjectLoader, UnableToLoadProjectError

BUILD_SCRIPT_FILENAME = 'build.craftr'


def context_factory(obj: t.Any) -> Context:
  if isinstance(obj, Extension):
    return ChainContext(ObjectContext(obj), ObjectContext(obj.ext))
  else:
    return ObjectContext(obj)


class CraftrDslProjectLoader(ProjectLoader):

  def __repr__(self) -> str:
    return f'{type(self).__name__}()'

  def load_project(self, project: 'Project') -> None:
    if not (filename := project.directory / BUILD_SCRIPT_FILENAME).exists():
      raise UnableToLoadProjectError(self, project)
    scope = {'__file__': str(filename), '__name__': project.name}
    Closure(None, None, project, context_factory).run_code(filename.read_text(), str(filename), scope=scope)
