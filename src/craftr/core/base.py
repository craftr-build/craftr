
"""
Core classes for the Craftr build framework.
"""

import abc
import dataclasses
import typing as t
from pathlib import Path

from .graph import Node, Graph

if t.TYPE_CHECKING:
  from .context import Context
  from .graph import Graph
  from .project import Project
  from .settings import Settings

T = t.TypeVar('T')
T_TaskOrAction = t.TypeVar('T_TaskOrAction', bound=t.Union['Action', 'Task'])

@dataclasses.dataclass
class ActionContext:
  verbose: bool


class Action(Node['Action']):

  @abc.abstractmethod
  def execute(self, context: ActionContext) -> None: ...


class Task(Node['Task']):

  project: 'Project'
  path: str
  group: t.Optional[str]
  default: bool
  description: t.Optional[str]
  finalized: bool
  always_outdated: bool

  @abc.abstractmethod
  def finalize(self) -> None: ...

  @abc.abstractmethod
  def get_action_graph(self) -> 'Graph[Action]': ...

  @abc.abstractmethod
  def is_outdated(self) -> bool: ...

  @abc.abstractmethod
  def complete(self) -> None: ...

  def get_node_id(self) -> str:
    return self.path


class TaskSelector(abc.ABC):

  @abc.abstractmethod
  def select_tasks(self, selection: str, project: 'Project') -> t.Collection['Task']: ...

  @abc.abstractmethod
  def select_default(self, project: 'Project') -> t.Collection['Task']: ...


class GraphExecutor(abc.ABC, t.Generic[T_TaskOrAction]):

  @abc.abstractmethod
  def execute(self, graph: 'Graph[T_TaskOrAction]') -> None: ...


class ProjectLoader(abc.ABC):

  @abc.abstractmethod
  def load_project(self, context: 'Context', parent: t.Optional['Project'], path: Path) -> 'Project': ...


class Plugin(abc.ABC):

  @abc.abstractmethod
  def apply(self, project: 'Project') -> t.Any: ...


class PluginLoader(abc.ABC):

  @abc.abstractmethod
  def load_plugin(self, plugin_name: str) -> Plugin: ...


class LoadableFromSettings(abc.ABC):

  @abc.abstractclassmethod
  def from_settings(cls: t.Type[T], settings: 'Settings') -> T: ...
