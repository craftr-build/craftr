
import typing as t
from collections.abc import MutableMapping
from pathlib import Path

from localimport import localimport  # type: ignore
from nr.caching.adapters.mapping import MappingAdapter
from nr.caching.adapters.json import JsonCache
from nr.caching.api import NamespaceStore
from nr.caching.stores.sqlite import SqliteStore

from ._execute import BuildGraph, Executor
from ._impl import (
  ChainingPluginLoader,
  ChainingProjectLoader,
  CraftrDslProjectLoader,
  DefaultBuildScriptConfigApplier,
  DefaultExecutor,
  DefaultTaskHashCalculator,
  DefaultProjectLoader,
  DefaultTaskSelector,
  EntrypointPluginLoader,
  ProjectPluginLoader)
from ._plugins import PluginLoader
from ._project import Project, ProjectLoader, BuildScriptConfig, BuildScriptConfigApplier
from ._settings import Settings
from ._tasks import TaskHashCalculator, TaskSelector, TaskSelection, select_tasks


class Context:

  settings: Settings
  root_project: Project
  kvstore: NamespaceStore
  json_cache: JsonCache
  project_loader: ProjectLoader
  task_hash_calculator: TaskHashCalculator
  task_hash_store: MutableMapping[str, str]
  task_selector: TaskSelector
  graph: BuildGraph
  executor: Executor
  buildscript_config_applier: BuildScriptConfigApplier
  packages_root: Path
  localimport: localimport
  plugin_loader: PluginLoader

  CRAFTR_SETTINGS_FILE = '.craftr.settings'

  def __init__(self, directory: t.Union[str, Path, None] = None, settings: t.Optional[Settings] = None) -> None:
    directory = Path(directory or Path.cwd())
    if settings is None:
      settings = Settings.from_file(directory / self.CRAFTR_SETTINGS_FILE)

    self.settings = settings
    self.root_project = Project(self, None, directory)
    self.root_project.build_directory.mkdir(exist_ok=True)

    self.kvstore = SqliteStore(str(self.root_project.build_directory / '.craftr.sqlite'))
    self.json_cache = JsonCache(self.kvstore.namespace('generic_json_cache'))
    self.project_loader = ChainingProjectLoader([DefaultProjectLoader(), CraftrDslProjectLoader()])
    self.task_hash_calculator = DefaultTaskHashCalculator()
    self.task_selector = DefaultTaskSelector()
    self.task_hash_store = MappingAdapter(self.kvstore.namespace('task_hashes'), str)
    self.graph = BuildGraph()
    self.executor = DefaultExecutor()
    self.buildscript_config_applier = DefaultBuildScriptConfigApplier()
    self.packages_root = self.root_project.build_directory / '.packages'
    self.localimport = localimport(self.buildscript_config_applier.get_additional_search_paths(self.packages_root))
    self.plugin_loader = ChainingPluginLoader([EntrypointPluginLoader(), ProjectPluginLoader(self.root_project)])

  def load_project(self) -> None:
    """
    Called to load the root project of the context.
    """

    self.project_loader.load_project(self.root_project)

  def init_project(self, project: Project) -> None:
    """ Must be called by a project loader to initialize the project, before it is executed. """

  def buildscript_config_apply(self, buildscript: BuildScriptConfig) -> None:
    """
    This is called when a project's buildscript was configured and should now be satisfied by installing
    the required dependencies into a local directory.
    """

    key = 'buildscript_config_applier_state'
    state = self.json_cache.load_or_none(key) or {}
    def persist():
      self.json_cache.store(key, state)
    self.buildscript_config_applier.apply(buildscript, self.packages_root, state, persist)
    persist()

  def execute(self, selection: TaskSelection = None) -> None:
    """
    Execute the tasks registered by the projects in this context.
    """

    self.root_project.finalize()
    tasks = select_tasks(self.task_selector, self.root_project, selection)
    assert all(t.finalized for t in tasks), 'some tasks not finalized?'
    self.graph.add_tasks(tasks)
    self.executor.execute(self, self.graph)
