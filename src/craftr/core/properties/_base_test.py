
import pytest
from pathlib import Path
from beartype.roar import BeartypeCallHintPepParamException
from ._base import HasProperties, Property, NoValueError


def test_property_get_set():
  p1 = Property[int]()
  p2 = Property[int](default=42)

  with pytest.raises(NoValueError):
    p1.get()
  assert p2.get() == 42

  p1.set(p2)
  assert p1.get() == 42
  assert p1.references == [p2]

  p1.set(10)
  assert p1.get() == 10
  assert p1.references == []


def test_property_beartype_check():
  p1 = Property[int]()
  with pytest.raises(BeartypeCallHintPepParamException):
    p1.set('foobar')  # type: ignore

  p2 = Property[Path]()
  with pytest.raises(BeartypeCallHintPepParamException):
    p2.set('foo/bar')  # type: ignore


def test_has_properties():

  class SomeClass(HasProperties):
    a: Property[str]
    b: Property[str]

  o = SomeClass()
  assert isinstance(o.a, Property)
  assert o.a._base_type is str
