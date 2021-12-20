
import pytest
from ._algorithms import topological_sort
from ._digraph import DiGraph
from ._digraph_test import diamond_graph


def test_topological_sort(diamond_graph: DiGraph):
  assert list(topological_sort(diamond_graph)) == ['a', 'c', 'b', 'd']


def test_topological_sort_cycle(diamond_graph: DiGraph):
  diamond_graph.node('f', None)
  diamond_graph.edge('f', 'a', None)
  diamond_graph.edge('d', 'a', None)
  with pytest.raises(RuntimeError):
    list(topological_sort(diamond_graph))
