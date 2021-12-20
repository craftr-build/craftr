
import abc
import dataclasses
import typing as t
from nr.pylang.utils.singletons import NotSet

K = t.TypeVar('K', bound=t.Hashable)
N = t.TypeVar('N')
E = t.TypeVar('E')


class DiGraph(t.Generic[K, N, E]):
  """
  Represents a directed graph.

  @generic N: The type of value stored for each node in the graph. All nodes in a graph are unique.
  @generic E: The type of value stored for each edge in the graph. Edge values may not be unique.
  """

  def __init__(self):
    """
    Create a new empty directed graph.
    """

    self._nodes: dict[K, '_Node[K, N]'] = {}
    self._roots: dict[K, None] = {}
    self._leafs: dict[K, None] = {}
    self._edges: dict[tuple[K, K], E] = {}
    self._nodesview = NodesView(self._nodes)
    self._edgesview = EdgesView(self._edges)

  @t.overload
  def node(self, node_id: K) -> N:
    """
    Retrieve a node from the graph by it's ID.

    @raises UnknownNodeError: If the node does not exist in the graph.
    """

  @t.overload
  def node(self, node_id: K, value: N) -> None:
    """
    Add a node to the graph. Overwrites the existing node value if the *node_id* already exists in the graph,
    but keeps its edges intact.
    """

  def node(self, node_id, value=NotSet.Value):
    if value is NotSet.Value:
      return self._get_node(node_id).value
    else:
      existing_node = self._nodes.get(node_id, NotSet.Value)
      if existing_node is NotSet.Value:
        predecessors, successors = {}, {}
        self._roots[node_id] = None
        self._leafs[node_id] = None
      else:
        predecessors, successors = existing_node.predecessors, existing_node.successors
      self._nodes[node_id] = _Node(value, predecessors, successors)

  @t.overload
  def edge(self, node_id1: K, node_id2: K) -> E:
    """
    Retrieves the value of an edge from the graph.

    @raises UnknownEdgeError: If the edge does not exist.
    """

  @t.overload
  def edge(self, node_id1: K, node_id2: K, value: E) -> None:
    """
    Adds a directed edge from *node_id1* to *node_id2* to the graph, storing the given value along the edge.
    Overwrites the value if the edge already exists. The edge's nodes must be present in the graph.

    @raises UnknownNodeError: If one of the nodes don't exist in the graph.
    """

  def edge(self, node_id1, node_id2, value=NotSet.Value):
    key = (node_id1, node_id2)
    if value is NotSet.Value:
      try:
        return self._edges[key]
      except KeyError:
        raise UnknownEdgeError(key)
    else:
      node1, node2 = self._get_node(node_id1), self._get_node(node_id2)
      self._edges[key] = value
      node1.successors[node_id2] = None
      node2.predecessors[node_id1] = None
      self._leafs.pop(node_id1, None)
      self._roots.pop(node_id2, None)

  @property
  def nodes(self) -> 'NodesView[K, N]':
    """
    Returns a view on the nodes in the graph.
    """

    return self._nodesview

  @property
  def edges(self) -> 'EdgesView[K, E]':
    """
    Returns a view on the edges in the graph.
    """

    return self._edgesview

  @property
  def roots(self) -> t.KeysView[K]:
    """
    Return the nodes of the graph that have no predecessors.
    """

    return self._roots.keys()

  @property
  def leafs(self) -> t.KeysView[K]:
    """
    Return the nodes of the graph that have no successors.
    """

    return self._leafs.keys()

  def predecessors(self, node_id: K) -> t.KeysView[K]:
    """
    Returns a sequence of the given node's predecessor node IDs.

    @raises UnknownNodeError: If the node does not exist.
    """

    return self._get_node(node_id).predecessors.keys()

  def successors(self, node_id: K) -> t.KeysView[K]:
    """
    Returns a sequence of the given node's successor node IDs.

    @raises UnknownNodeError: If the node does not exist.
    """

    return self._get_node(node_id).successors.keys()

  # Internal

  def _get_node(self, node_id: K) -> '_Node[K, N]':
    try:
      return self._nodes[node_id]
    except KeyError:
      raise UnknownNodeError(node_id)


@dataclasses.dataclass
class _Node(t.Generic[K, N]):
  value: N
  predecessors: dict[K, None]
  successors: dict[K, None]


class NodesView(t.Generic[K, N]):

  def __init__(self, nodes: dict[K, _Node[K, N]]) -> None:
    self._nodes = nodes

  def __repr__(self) -> str:
    return f'<NodesView count={len(self)}>'

  def __contains__(self, node_id: K) -> bool:
    return node_id in self._nodes

  def __len__(self) -> int:
    return len(self._nodes)

  def __iter__(self) -> t.Iterator[K]:
    return iter(self._nodes)


class EdgesView(t.Generic[K, E]):

  def __init__(self, edges: dict[tuple[K, K], E]) -> None:
    self._edges = edges

  def __repr__(self) -> str:
    return f'<EdgesView count={len(self)}>'

  def __contains__(self, edge: tuple[K, K]) -> bool:
    return edge in self._edges

  def __len__(self) -> int:
    return len(self._edges)

  def __iter__(self) -> t.Iterator[tuple[K, K]]:
    return iter(self._edges)


class UnknownNodeError(KeyError):
  pass


class UnknownEdgeError(KeyError):
  pass
