
import dataclasses
import typing as t
import weakref

T = t.TypeVar('T')
WhenReadyCallback = t.Callable[['BaseGraph[T]'], None]


class _GraphElement(t.Generic[T]):

  _graph: t.Optional['weakref.ReferenceType[BaseGraph[T]]'] = None

  @property
  def graph(self) -> 'BaseGraph[T]':
    if self._graph is None:
      raise RuntimeError('not attached to a graph')
    graph = self._graph()
    if graph is None:
      raise RuntimeError('lost reference to graph')
    return graph


@dataclasses.dataclass
class Node(_GraphElement[T]):
  """
  Represents a node in a directed graph, which wraps a value.
  """

  id: str
  contents: T
  dependencies: t.List[t.Union['NodeGroup[T]', 'Node[T]']]
  group: t.Optional['NodeGroup[T]'] = None

  def __repr__(self) -> str:
    return f'Node(id={self.id!r}, group={self.group!r})'


@dataclasses.dataclass
class NodeGroup(_GraphElement[T]):
  """
  Represents a group of nodes that may imply additional dependencies between the nodes that it contains and
  another node or node group that this group depends on.
  """

  id: str
  contents: t.List[Node[T]]
  dependencies: t.List[t.Union['NodeGroup[T]', 'Node[T]']]
  linear: bool = False

  def __repr__(self) -> str:
    return f'NodeGroup(id={self.id!r}, linear={self.linear!r})'


class BaseGraph(t.Generic[T]):
  """
  Basic graph implementation. Can only deal with #Node and #NodeGroup objects directly and does not accept
  bare values of the generic type *T*.
  """

  def __init__(self) -> None:
    self._finalized = False
    self._nodes: t.Dict[str, Node[T]] = {}
    self._groups: t.Dict[str, NodeGroup[T]] = {}

  def __contains__(self, node_id: t.Union[str, Node[T]]) -> bool:
    if isinstance(node_id, Node):
      node = node_id
      return node.id in self._nodes and self._nodes[node.id] is node
    else:
      return node_id in self._nodes

  def __getitem__(self, node_id: str) -> Node[T]:
    return self.node(node_id)

  def node(self, node_id: str) -> Node[T]:
    return self._nodes[node_id]

  def group(self, group_id: str) -> Node[T]:
    return self._groups[group_id]

  def dependencies_of(self, node: Node[T]) -> t.Iterator[Node[T]]:
    seen: t.Set[str] = set()

    # Depend on the previous node in the group if the group is lienar.
    if node.group and node.group.linear:
      index = node.group.contents.index(node)
      if index > 0:
        yield node.group.contents[index - 1]

    # Depend on the immediate dependencies of the node and its groups.
    for dep in node.dependencies + (node.group.dependencies if node.group else []):
      if isinstance(dep, Node):
        if dep.id not in seen:
          yield dep
          seen.add(dep.id)
      elif isinstance(dep, NodeGroup):
        yield from dep.contents

  def add(self, arg: t.Union[NodeGroup[T], Node[T]], group: t.Optional[NodeGroup[T]] = None) -> None:
    if self._finalized:
      raise RuntimeError('cannot add to graph because it is finalized')
    if group is not None and not isinstance(arg, Node):
      raise TypeError('need Node if group is specified')
    if isinstance(arg, Node):
      node = arg
      if group is not None:
        if node.group is not None:
          raise RuntimeError(f'node {node.id!r} is already assigned to a group')
        assert node not in group.contents
        group.contents.append(node)
        node.group = group
      if node.id in self._nodes:
        if self._nodes[node.id] is not node:
          raise RuntimeError('different Node, same id')
      else:
        self._nodes[node.id] = node
        node._graph = weakref.ref(self)
    elif isinstance(arg, NodeGroup):
      group = arg
      if group.id in self._groups:
        if self._groups[group.id] is not group:
          raise RuntimeError('different NdoeGroup, same id')
      else:
        self._groups[group.id] = group
        group._graph = weakref.ref(self)
      for node in group.contents:
        self.add(node)
    else:
      raise TypeError(f'expected Node or NodeGroup, got {type(arg).__name__}')
    for dep in arg.dependencies:
      self.add(dep)

  def finalize(self) -> None:
    """
    Finalize the graph, walking through all nodes and groups once more to make sure all dependencies listed
    in them are known to the graph.
    """

    if self._finalized:
      return

    for node in self._nodes.values():
      self.add(node)
    for group in self._groups.values():
      self.add(group)

    self._finalized = True

  def execution_order(self) -> t.List[Node[T]]:
    result: t.List[Node[T]] = []
    result_seen: t.Set[str] = set()

    def _handle_node(node: Node[T], local_seen: t.Set[str]) -> None:
      if node.id not in self._nodes:
        raise RuntimeError(f'encountered node that does not exist in the graph: {node.id!r}')
      if node.id in local_seen:
        return #raise RuntimeError(f'cyclic dependency graph involving task {node.id!r}: {result}')
      local_seen.add(node.id)
      for dep in self.dependencies_of(node):
        _handle_node(dep, local_seen)
      if node.id not in result_seen:
        result.append(node)
        result_seen.add(node.id)

    for node in self._nodes.values():
      _handle_node(node, set())

    return result


class NodeHandler(t.Protocol[T]):
  """
  The node handler deals with the construction of nodes. A handler is only needed when using the #Graph class
  (instead of the #BaseGraph which is a more basic class).
  """

  def get_node_id(self, obj: T) -> str:
    raise NotImplementedError

  def create_node(self, obj: T, graph: 'Graph[T]') -> Node[T]:
    """
    Create a node for the given object. This is called by the #Graph when there is no node for the given object. The
    method should construct the full dependencies of *obj* recursively. It is recommended to use #Graph.allocate_node()
    which will raise an exception if the node already exists.
    """

    raise NotImplementedError


class Graph(BaseGraph[T]):
  """
  Represents a graph of nodes that can give you an execution order.
  """

  def __init__(self, handler: NodeHandler[T]) -> None:
    super().__init__()
    self._handler = handler
    self._ready = False
    self._when_ready_callbacks: t.List[WhenReadyCallback] = []

  def when_ready(self, callback: WhenReadyCallback) -> None:
    if self._finalized:
      callback(self)
    else:
      self._when_ready_callbacks.append(callback)

  def allocate_node(self, content: T) -> Node[T]:
    node_id = self._handler.get_node_id(content)
    if node_id in self:
      raise RuntimeError(f'cannot allocate node {node_id!r} as it already exists in the graph')
    node = Node(node_id, content, [], None)
    self.add(node)
    return node

  def allocate_group(self, group_id: str, linear: bool = False) -> NodeGroup[T]:
    try:
      self.group(group_id)
    except KeyError:
      pass
    else:
      raise RuntimeError(f'group {group_id!r} already exists')
    group = NodeGroup(group_id, [], [], linear)
    self.add(group)
    return group

  # BaseGraph

  def __contains__(self, node_id: t.Union[str, T]) -> bool:
    if not isinstance(node_id, str):
      node_id = self._handler.get_node_id(node_id)
    return super().__contains__(node_id)

  def __getitem__(self, node_id: t.Union[str, T]) -> Node[T]:
    return self.node(node_id, False)

  def node(self, node_id: t.Union[str, T], create_if_not_exists: bool = True) -> Node[T]:
    if not isinstance(node_id, str):
      obj = node_id
      node_id = self._handler.get_node_id(obj)
      if create_if_not_exists and node_id not in self:
        return self._handler.create_node(obj, self)
    return super().node(node_id)

  def add(self, arg: t.Union[NodeGroup[T], Node[T], T], group: t.Optional[NodeGroup[T]] = None) -> Node[T]:
    if not isinstance(arg, (NodeGroup, Node)):
      arg = self.node(arg, True)
    super().add(arg, group)

  def dependencies_of(self, node: t.Union[str, Node[T], T]) -> t.Iterator[Node[T]]:
    if not isinstance(node, Node):
      assert not isinstance(node, NodeGroup)
      node = self[node]
    return super().dependencies_of(node)

  def finalize(self) -> None:
    was_finalized = self._finalized
    super().finalize()
    if not was_finalized:
      for callback in self._when_ready_callbacks:
        callback(self)
