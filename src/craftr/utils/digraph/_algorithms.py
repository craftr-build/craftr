
import copy
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
      raise RuntimeError(f'encountered a cycle in the graph at {seen & roots}')
    seen.update(roots)
    yield from roots
    roots = {
      k: None
      for n in roots for k in sorted(graph.successors(n))
      if not graph.predecessors(k) - seen
    }.keys()

  if len(seen) != len(graph.nodes):
    raise RuntimeError(f'encountered a cycle in the graph (unreached nodes {set(graph.nodes) - seen})')
