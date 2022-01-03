

from pathlib import Path

from ._path import PathListProperty, PathProperty


def test_path_property():
  p1 = PathProperty()
  p1.set('foo/bar')
  assert p1.get() == Path('foo/bar')


def test_path_list_property():
  p1 = PathListProperty()
  p1.set(['foo/bar'])
  assert p1.get() == [Path('foo/bar')]
  p1.append('/baz/bang')
  assert p1.get() == [Path('foo/bar'), Path('/baz/bang')]

  p2 = PathProperty(default='spam/eggs')
  p1.set([p2])
  p1.append(p2)
  assert p1.get() == [Path('spam/eggs')] * 2
  assert p1.references == [p2, p2]

  p1.clear()
  assert p1.get() == []
  assert p1.references == []
