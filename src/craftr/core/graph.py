
import abc
import typing as t

from nr.preconditions import check_argument

T = t.TypeVar('T')
T_Node = t.TypeVar('T_Node', bound='Node')
WhenReadyCallback = t.Callable[['Graph[T]'], None]


class Node(abc.ABC, t.Generic[T]):
  """
  Base class for objects that have dependencies.
  """

  dependencies: t.List[T]

  def __init__(self) -> None:
    self.dependencies = []

  def get_node_id(self) -> str:
    return str(id(self))

  def depends_on(self, *nodes: 'Node[T]') -> None:
    self.dependencies.extend(nodes)


class Graph(t.Generic[T_Node]):
  """
  Represents a graph of nodes that can give you the execution order.
  """

  def __init__(self, init_nodes: t.Optional[t.Iterable[T_Node]] = None):
    self._ready = False
    self._nodes: t.Dict[str, T_Node] = {}
    self._when_ready_callbacks: t.List[WhenReadyCallback] = []
    self.add(*(init_nodes or []))

  @property
  def is_ready(self) -> bool:
    return self._ready

  def ready(self) -> None:
    """ Declare that the execution graph is ready. Invokes registered listeners. """

    if not self._ready:
      self._ready = True
      for callback in self._when_ready_callbacks:
        callback(self)

  def when_ready(self, closure: WhenReadyCallback) -> None:
    """
    Adds a callback that is invoked when the execution graph is ready. If the graph is ready
    by the time this method is called, the *closure* is invoked immediately.
    """

    if self._ready:
      closure(self)
    else:
      self._when_ready_callbacks.append(closure)

  def add(self, *nodes: T_Node) -> None:
    """ Add a node and all it's dependencies to the graph. """

    if self._ready:
      raise RuntimeError('cannot add more nodes to ready Graph')

    for node in nodes:
      if not self._contains(node):
        self._nodes[node.get_node_id()] = node
      for dependency in node.dependencies:
        self.add(dependency)

  def has(self, node: t.Union[str, T_Node]) -> bool:
    """
    Returns `True` if the specified *node* (either the node ID or the node itself) is contained in the graph.
    """

    if isinstance(node, str):
      return node in self._nodes
    return self._contains(node)

  def nodes(self) -> t.Iterator[T_Node]:
    return self._nodes.values()

  def _contains(self, node: T_Node) -> bool:
    if node.get_node_id() in self._nodes:
      check_argument(node is self._nodes[node.get_node_id()],
        f'same path but different task instance: {node.get_node_id()!r}')
      return True
    return False

  def execution_order(self) -> t.List[T_Node]:
    """
    Retrieve the nodes of the graph in the order that they need to be executed.
    """

    result: t.List[T_Node] = []

    def add(task: T_Node, seen: t.Set[T_Node]) -> None:
      if not self._contains(task):
        return
      if task in seen:
        raise RuntimeError(f'cyclic dependency graph involving task {task.path!r}')
      seen.add(task)
      for dep in task.dependencies:
        add(dep, seen)
      if task not in result:
        result.append(task)

    for task in self._nodes.values():
      add(task, set())

    return result
