
import typing as t
from ._digraph import DiGraph, K, N, E


def topological_sort(graph: DiGraph[K, N, E]) -> t.Iterator[K]:
  """
  Calculate the topological order for elements in the *graph*.

  @raises RuntimeError: If there is a cycle in the graph.
  """

  seen: set[K] = set()
  roots = graph.roots

  while roots:
    if seen & roots:
      raise RuntimeError('encountered a cycle in the graph')
    seen.update(roots)
    yield from roots
    roots = {k: None for n in roots for k in graph.successors(n)}.keys()

  if len(seen) != len(graph.nodes):
    raise RuntimeError('encountered a cycle in the graph')
