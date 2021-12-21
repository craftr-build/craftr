
import typing as t
from collections.abc import Mapping
from pathlib import Path

from nr.caching.adapters.mapping import MappingAdapter
from nr.caching.api import NamespaceStore
from nr.caching.stores.sqlite import SqliteStore
from ._tasks import TaskHashCalculator
from ._project import Project, ProjectLoader
from ._impl import ChainingProjectLoader, CraftrDslProjectLoader, DefaultTaskHashCalculator, DefaultProjectLoader
from ._settings import Settings


class Context:

  settings: Settings
  root_project: Project
  kvstore: NamespaceStore
  project_loader: ProjectLoader
  task_hash_calculator: TaskHashCalculator
  task_hash_store: Mapping[str, str]

  def __init__(self, directory: t.Union[str, Path, None] = None, settings: t.Optional[Settings] = None) -> None:
    directory = Path(directory or Path.cwd())
    if settings is None:
      settings = Settings.from_file(directory / '.craftr.settings')
    self.settings = settings
    self.root_project = Project(self, None, directory)
    self.root_project.build_directory.mkdir(exist_ok=True)
    self.kvstore = SqliteStore(str(self.root_project.build_directory / '.craftr.sqlite'))
    self.project_loader = ChainingProjectLoader([DefaultProjectLoader(), CraftrDslProjectLoader()])
    self.task_hash_calculator = DefaultTaskHashCalculator()
    self.task_hash_store = MappingAdapter(self.kvstore.namespace('task_hashes'), str)
