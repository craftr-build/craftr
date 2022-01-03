import dataclasses
import typing as t
import weakref
from collections.abc import Mapping

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
    self._nodesview = NodesView(self)
    self._edgesview = EdgesView(self)

  def add_node(self, node_id: K, value: N) -> None:
    """
    Add a node to the graph. Overwrites the existing node value if the *node_id* already exists in the graph,
    but keeps its edges intact.
    """

    existing_node = self._nodes.get(node_id, NotSet.Value)
    if existing_node is NotSet.Value:
      predecessors, successors = {}, {}
      self._roots[node_id] = None
      self._leafs[node_id] = None
    else:
      predecessors, successors = existing_node.predecessors, existing_node.successors
    self._nodes[node_id] = _Node(value, predecessors, successors)

  def add_edge(self, node_id1: K, node_id2: K, value: E) -> None:
    """
    Adds a directed edge from *node_id1* to *node_id2* to the graph, storing the given value along the edge.
    Overwrites the value if the edge already exists. The edge's nodes must be present in the graph.

    @raises UnknownNodeError: If one of the nodes don't exist in the graph.
    """

    node1, node2 = self._get_node(node_id1), self._get_node(node_id2)
    self._edges[(node_id1, node_id2)] = value
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


class NodesView(Mapping[K, N]):

  def __init__(self, g: DiGraph[K, N, t.Any]) -> None:
    self._g = weakref.ref(g)
    self._nodes = g._nodes

  def __repr__(self) -> str:
    return f'<NodesView count={len(self)}>'

  def __contains__(self, node_id: object) -> bool:
    return node_id in self._nodes

  def __len__(self) -> int:
    return len(self._nodes)

  def __iter__(self) -> t.Iterator[K]:
    return iter(self._nodes)

  def __getitem__(self, key: K) -> N:
    try:
      return self._nodes[key].value
    except KeyError:
      raise UnknownNodeError(key)

  def __setitem__(self, key: K, value: N) -> None:
    g = self._g()
    assert g is not None
    g.add_node(key, value)

  def __delitem__(self, key: K) -> None:
    g = self._g()
    assert g is not None
    node = g._nodes.pop(key)
    for pred in node.predecessors:
      g._nodes[pred].successors.pop(key)
      del g._edges[(pred, key)]
    for succ in node.successors:
      g._nodes[succ].predecessors.pop(key)
      del g._edges[(key, succ)]
    g._roots.pop(key, None)
    g._leafs.pop(key, None)


class EdgesView(Mapping[tuple[K, K], E]):

  def __init__(self, g: DiGraph[K, t.Any, E]) -> None:
    self._g = weakref.ref(g)
    self._edges = g._edges

  def __repr__(self) -> str:
    return f'<EdgesView count={len(self)}>'

  def __contains__(self, edge: object) -> bool:
    return edge in self._edges

  def __len__(self) -> int:
    return len(self._edges)

  def __iter__(self) -> t.Iterator[tuple[K, K]]:
    return iter(self._edges)

  def __getitem__(self, key: tuple[K, K]) -> E:
    try:
      return self._edges[key]
    except KeyError:
      raise UnknownEdgeError(key)

  def __setitem__(self, key: tuple[K, K], value: E) -> None:
    g = self._g()
    assert g is not None
    g.add_edge(key[0], key[1], value)

  def __delitem__(self, key: tuple[K, K]) -> None:
    del self._edges[key]


class UnknownNodeError(KeyError):
  pass


class UnknownEdgeError(KeyError):
  pass
