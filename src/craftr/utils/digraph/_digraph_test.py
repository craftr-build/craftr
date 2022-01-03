
import pytest
from ._digraph import DiGraph, UnknownEdgeError, UnknownNodeError


@pytest.fixture
def diamond_graph() -> DiGraph[str, None, None]:
  g = DiGraph[str, None, None]()
  g.node('a', None)
  g.node('b', None)
  g.node('c', None)
  g.node('d', None)
  g.edge('a', 'b', None)
  g.edge('b', 'd', None)
  g.edge('a', 'c', None)
  g.edge('c', 'd', None)
  return g


@pytest.fixture
def diamond_cross_graph(diamond_graph: DiGraph[str, None, None]) -> DiGraph[str, None, None]:
  diamond_graph.edge('a', 'd', None)
  return diamond_graph


def test_diamond_graph(diamond_graph: DiGraph):
  g = diamond_graph
  assert 'a' in g.nodes
  assert ('a', 'c') in g.edges
  assert ('a', 'd') not in g.edges
  assert list(g.nodes) == ['a', 'b', 'c', 'd']
  assert list(g.edges) == [('a', 'b'), ('b', 'd'), ('a', 'c'), ('c', 'd')]

  with pytest.raises(UnknownNodeError):
    g.node('f')
  with pytest.raises(UnknownEdgeError):
    g.edge('a', 'd')

  assert g.roots == {'a'}
  assert g.leafs == {'d'}

  assert g.predecessors('a') == set()
  assert g.predecessors('b') == {'a'}
  assert g.successors('a') == {'b', 'c'}
