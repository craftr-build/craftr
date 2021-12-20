
import abc
import copy
import typing as t
import weakref

from craftr.utils.beartype import beartype_check, TypeHint
from nr.pylang.utils.singletons import NotSet

T = t.TypeVar('T')
T_Property = t.TypeVar('T_Property', bound='Property')


class HasProperties(abc.ABC):
  """
  Base class for classes that have properties declared on the class level. When an instance of the class
  is created, its properties will be copied and bound to the instance.
  """

  __properties__: t.ClassVar[dict[str, 'Property']]

  def __init_subclass__(cls) -> None:
    cls.__properties__ = {}
    for key in dir(cls):
      value = getattr(cls, key)
      if isinstance(value, Property):
        assert value._name is None or value._name == key, (key, value)
        value._name = key
        cls.__properties__[key] = value

  def __init__(self) -> None:
    super().__init__()
    for key, value in self.__properties__.items():
      setattr(self, key, value._bound_copy(self))


class Property(t.Generic[T]):
  """
  The base class for properties on tasks. Properties are the preferred way to make task implementation configurable
  as they make tracking dependencies between tasks easier. Properties
  """

  _base_type: t.Optional[TypeHint] = None

  def __init__(
    self, *,
    default: t.Union[T, NotSet] = NotSet.Value,
    base_type: t.Union[TypeHint, None, NotSet] = NotSet.Value,
  ) -> None:
    self._default = default
    self._value: t.Union[T, NotSet] = default
    self._name: t.Optional[str] = None
    self._owner: t.Optional[weakref.ReferenceType] = None
    self._references: list['Property[T]'] = []
    if base_type is not NotSet.Value:
      self._base_type = base_type

  def __class_getitem__(cls, type_hint: t.Type[T]) -> t.Type['Property[T]']:
    return _PropertyGenericAlias(cls, type_hint)  # type: ignore

  def __repr__(self) -> str:
    return f'{type(self).__name__}(name={self._name!r})'

  def _bound_copy(self: T_Property, owner: object) -> T_Property:
    new_self = copy.copy(self)
    new_self._owner = weakref.ref(owner)
    if self._default is not NotSet.Value:
      new_self._value = copy.deepcopy(self._default)
    return new_self

  def is_set(self) -> bool:
    return self._value is not NotSet.Value

  def get(self) -> T:
    if self._value is NotSet.Value:
      raise NoValueError(f'property {self._name!r} has no value set')
    return self._value

  def set(self, value: t.Union[T, 'Property[T]']) -> None:
    if isinstance(value, Property):
      self._references = [value]
      value = value.get()
    else:
      self._references = []
    if self._base_type is not None:
      beartype_check(value, self._base_type)
    self._value = value

  @property
  def name(self) -> str:
    assert self._name is not None
    return self._name

  @property
  def owner(self) -> object:
    if self._owner:
      value = self._owner()
      if value is None:
        raise RuntimeError('lost reference to property owner')
      return value
    return None

  @property
  def references(self) -> list['Property[T]']:
    return self._references


class NoValueError(Exception):
  pass


class _PropertyGenericAlias:

  def __init__(self, property_cls: t.Type[Property], type_hint: TypeHint) -> None:
    self._property_cls = property_cls
    self._type_hint = type_hint

  def __call__(self, *args, **kwargs) -> Property:
    return Property(*args, **kwargs, base_type=self._type_hint)
