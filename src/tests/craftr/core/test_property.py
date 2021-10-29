# type: ignore

import enum
import typing as t
from pathlib import Path
import pytest
import typing_extensions as te
from craftr.core.property import Box, ListProperty, Property, HavingProperties


def test_having_properties_constructor():

  class MyClass(HavingProperties):
    a = Property(int)
    b = Property(str)

  assert MyClass().get_properties().keys() == set(['a', 'b'])

  obj = MyClass()
  obj.a.set(42)
  obj.b.set('foo')

  assert obj.a.get() == 42
  assert obj.b.get() == 'foo'


def test_property_set_value_1():

  class MyClass(HavingProperties):
    a = Property(int)
    b = ListProperty(str)

  obj = MyClass()

  obj.a.set('bar')
  assert obj.a.get() == 'bar'

  obj.a.set(Box('foo'))
  assert obj.a.get() == 'foo'


def test_property_annotation_in_value_hint():

  class MyClass(HavingProperties):
    a = Property(int, default=42)
    b = Property(str)

  obj = MyClass()

  assert obj.get_properties()['a'].type == int
  assert obj.get_properties()['a'].default == 42

  assert obj.get_properties()['b'].type == str
  assert obj.get_properties()['b'].default is None


def test_property_operators():
  # Test concatenation if the property value is populated.
  prop1 = ListProperty(str, name='prop1')
  prop1.set(['hello'])
  assert (prop1 + ['world']).get() == ['hello', 'world']

  prop1 = Property(str, name='prop1')
  prop1.set('hello')
  assert (prop1 + ' world').get() == 'hello world'

  # Concatenating an un-set property will fall back to an empty default.
  prop1 = ListProperty(str, name='prop1')
  assert (prop1 + ['value']).get() == ['value']

  prop1 = Property(str, name='prop1')
  assert (prop1 + 'value').get() == 'value'


def test_property_nesting_1():
  prop1 = ListProperty(str, name='prop1')
  prop2 = Property(str, name='prop2')
  prop1.set(['hello', prop2])
  prop2.set('world')
  assert prop1.get() == ['hello', 'world']


def test_property_enum_coercion():
  class MyEnum(enum.Enum):
    ABC = enum.auto()

  prop = Property(MyEnum)
  prop.set('abc')
  assert prop.get() == MyEnum.ABC

  prop = ListProperty(MyEnum)
  prop.set(['abc'])
  assert prop.get() == [MyEnum.ABC]


def test_property_path_coercion():
  prop = Property(Path)
  prop.set('hello/world.c')
  assert prop.get() == Path('hello/world.c')

  prop = ListProperty(Path)
  prop.set({'hello/world.c'})
  assert prop.get() == [Path('hello/world.c')]
