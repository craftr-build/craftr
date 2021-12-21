
import typing as t
from collections.abc import Collection, MutableMapping
from pathlib import Path

from nr.caching.adapters.mapping import MappingAdapter
from nr.caching.api import NamespaceStore
from nr.caching.stores.sqlite import SqliteStore

from craftr.utils.digraph import DiGraph, topological_sort
from ._tasks import Task, TaskHashCalculator, TaskSelector, TaskSelection, select_tasks
from ._project import Project, ProjectLoader
from ._impl import (ChainingProjectLoader, CraftrDslProjectLoader, DefaultTaskHashCalculator,
  DefaultProjectLoader, DefaultTaskSelector)
from ._settings import Settings


class Context:

  settings: Settings
  root_project: Project
  kvstore: NamespaceStore
  project_loader: ProjectLoader
  task_hash_calculator: TaskHashCalculator
  task_hash_store: MutableMapping[str, str]
  task_selector: TaskSelector
  graph: 'BuildGraph'

  CRAFTR_SETTINGS_FILE = '.craftr.settings'

  def __init__(self, directory: t.Union[str, Path, None] = None, settings: t.Optional[Settings] = None) -> None:
    directory = Path(directory or Path.cwd())
    if settings is None:
      settings = Settings.from_file(directory / self.CRAFTR_SETTINGS_FILE)
    self.settings = settings
    self.project_loader = ChainingProjectLoader([DefaultProjectLoader(), CraftrDslProjectLoader()])
    self.task_hash_calculator = DefaultTaskHashCalculator()
    self.task_selector = DefaultTaskSelector()
    self.graph = BuildGraph()

  def init_project(self, project: Project) -> None:
    """ Must be called by a project loader to initialize the project, before it is executed. """

  def load_project(self, path: Path) -> None:
    """
    Called to load the root project of the context. This must be called before the Context can be fully
    utilized as it will finalize the initialization.
    """

    self.root_project = self.project_loader.load_project(self, None, path)
    self.root_project.build_directory.mkdir(exist_ok=True)
    self.kvstore = SqliteStore(str(self.root_project.build_directory / '.craftr.sqlite'))
    self.task_hash_store = MappingAdapter(self.kvstore.namespace('task_hashes'), str)

  def execute(self, selection: TaskSelection = None) -> None:
    """
    Execute the tasks registered by the projects in this context.
    """

    self.root_project.finalize()
    tasks = select_tasks(self.task_selector, self.root_project, selection)
    assert all(t.finalized for t in tasks), 'some tasks not finalized?'
    self.graph.add_tasks(tasks)


class BuildGraph(DiGraph[str, Task, None]):

  def __init__(self) -> None:
    super().__init__()

  def add_tasks(self, tasks: Collection[Task], *, seen: t.Optional[set[Task]] = None) -> None:
    if seen is None:
      seen = set()
    for task in set(tasks):
      if task in seen:
        raise RuntimeError('cyclic dependency')
      seen.add(task)
      self.node(task.path, task)
      for dep in task.dependencies:
        self.node(dep.path, dep)
        self.edge(dep.path, task.path, None)
      self.add_tasks(task.dependencies, seen=seen)

  def execution_order(self) -> list[Task]:
    return [self.nodes[k] for k in topological_sort(self)]
