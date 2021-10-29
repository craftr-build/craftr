
import dataclasses
import typing as t
from craftr.core.graph import Node, NodeGroup, NodeHandler, Graph


@dataclasses.dataclass
class Action:
  id: str
  dependencies: t.Sequence['Action'] = ()


class ActionHandler(NodeHandler[Action]):

  def get_node_id(self, obj: Action) -> str:
    return obj.id

  def create_node(self, obj: Action, graph: 'Graph[Action]') -> Node[Action]:
    node = graph.allocate_node(obj)
    node.dependencies = [graph.node(d) for d in obj.dependencies]
    return node


def test_graph1():
  g = Graph(ActionHandler())
  a1 = Action('a1')
  a2 = Action('a2', [a1])
  g.add(a2)

  assert list(g.dependencies_of(a1)) == []
  assert list(g.dependencies_of(a2)) == [g[a1]]

  g.finalize()
  n1, n2 = list(g.execution_order())
  assert n1.contents is a1
  assert n2.contents is a2


def test_graph2_node_groups():
  g = Graph(ActionHandler())

  group1 = g.allocate_group('first', linear=True)
  g.add(Action('a1'), group1)
  assert g['a1'].group is group1
  g.add(Action('a2'), group1)

  group2 = g.allocate_group('second')
  b1 = Action('b1')
  b2 = Action('b2')
  b3 = Action('b3')
  b2.dependencies = [b3]
  g.add(b1, group2)
  g.add(b2, group2)
  g.add(b3, group2)
  group2.dependencies.append(group1)

  c1 = Action('c1')
  g.node(c1).dependencies.append(group2)

  g.finalize()
  order = [x.id for x in g.execution_order()]
  assert order == ['a1', 'a2', 'b1', 'b3', 'b2', 'c1']
