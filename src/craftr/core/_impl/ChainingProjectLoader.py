
import logging
import typing as t
from pathlib import Path

from .._project import Project, ProjectLoader, UnableToLoadProjectError
from .._settings import Settings, LoadableFromSettings

if t.TYPE_CHECKING:
  from .._context import Context


class ChainingProjectLoader(ProjectLoader, LoadableFromSettings):
  """
  Delegates the project loading process to a sequence of other loaders. Returns the first project loaded by any loader.

  If created from configuration, the `craftr.plugin.loader.delegates` option is respected, which must be a
  comma-separated list of fully qualified lodaer names. A loader name may be trailed by a question mark to ignore
  if the loader name cannot be resolved.
  """

  log = logging.getLogger(__qualname__ + '.' + __name__)  # type: ignore

  DEFAULT_DELEGATES = 'craftr.core.impl.DefaultProjectLoader:DefaultProjectLoader,craftr.build.loader:DslProjectLoader?'

  def __init__(self, delegates: t.List[ProjectLoader]) -> None:
    self.delegates = delegates

  def __repr__(self) -> str:
    return f'{type(self).__name__}(delegates={self.delegates!r})'

  def load_project(self, context: 'Context', parent: t.Optional['Project'], path: Path) -> 'Project':
    for delegate in self.delegates:
      try:
        return delegate.load_project(context, parent, path)
      except UnableToLoadProjectError:
        pass
    raise UnableToLoadProjectError(self, context, parent, path)

  @classmethod
  def from_settings(cls, settings: 'Settings') -> 'ChainingProjectLoader':
    delegates: t.List[ProjectLoader] = []
    names = settings.get('core.plugin.loader.delegates', cls.DEFAULT_DELEGATES).split(',')
    for name in map(str.strip, names):
      ignore_unresolved = name.endswith('?')
      if ignore_unresolved:
        name = name[:-1]
      try:
        delegates.append(settings.create_instance(ProjectLoader, name))  # type: ignore
      except ImportError as exc:
        if ignore_unresolved:
          cls.log.warn('unable to resolve delegate project loader "%s": %s', name, exc)
        else:
          raise
    return cls(delegates)
