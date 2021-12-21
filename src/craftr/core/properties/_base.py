
import abc
import copy
import typing as t
import weakref

from craftr.utils.beartype import beartype_check, TypeHint
from nr.pylang.utils.singletons import NotSet

T = t.TypeVar('T')
T_Property = t.TypeVar('T_Property', bound='Property')
R = t.TypeVar('R')
_GenericAlias = t._GenericAlias  # type: ignore


class HasProperties(abc.ABC):
  """
  Base class for classes that have properties declared on the class level. When an instance of the class
  is created, its properties will be copied and bound to the instance.
  """

  __properties__: t.ClassVar[dict[str, 'Property']] = {}

  def __init_subclass__(cls) -> None:
    cls.__properties__ = {}
    for base in cls.__bases__:
      if issubclass(base, HasProperties):
        cls.__properties__.update(base.__properties__)
    for key in dir(cls):
      value = getattr(cls, key, None)
      if isinstance(value, Property):
        assert value._name is None or value._name == key, (key, value)
        value._name = key
        cls.__properties__[key] = value
    for key, value in cls.__annotations__.items():
      origin = value.__origin__ if isinstance(value, _GenericAlias) else value
      if (isinstance(origin, type) and issubclass(origin, Property)):
        cls.__properties__[key] = value()

  def __init__(self) -> None:
    super().__init__()
    for key, value in self.__properties__.items():
      setattr(self, key, value._bound_copy(self))

  def get_properties(self) -> t.Dict[str, 'Property']:
    return {k: getattr(self, k) for k in self.__properties__}


class Property(t.Generic[T]):
  """
  The base class for properties on tasks. Properties are the preferred way to make task implementation
  configurable as they make tracking dependencies between tasks easier.
  """

  def __init__(
    self, *,
    default: t.Union[T, NotSet] = NotSet.Value,
    base_type: t.Union[TypeHint, None] = None,
    **kwargs,
  ) -> None:
    """
    Create a new property.

    @param default: The default value of the property.
    @param base_type: The type of the values that the property should hold. When setting the value of a
      property, its type will be validated using {@link beartype}.
    """

    super().__init__(**kwargs)

    self._default = default
    self._base_type = base_type
    self._value: t.Union[T, NotSet] = NotSet.Value
    self._name: t.Optional[str] = None
    self._owner: t.Optional[weakref.ReferenceType] = None
    self._references: list['Property'] = []
    self._value_adapters: list[t.Callable[[object, list[Property]], object]] = []
    self.__post_init__()
    if default is not NotSet.Value:
      self.set(default)

  def __post_init__(self) -> None:
    pass

  def __class_getitem__(cls, type_hint: t.Type[T]) -> t.Type['Property[T]']:
    return _PropertyGenericAlias(cls, (type_hint,))  # type: ignore

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

  @t.overload
  def get(self) -> T: ...

  @t.overload
  def get(self, default: R) -> t.Union[T, R]: ...

  def get(self, default=NotSet.Value):
    if self._value is NotSet.Value:
      if default is NotSet.Value:
        raise NoValueError(f'property {self._name!r} has no value set')
      return default
    return self._value

  def set(self, value: t.Union[T, 'Property[T]']) -> None:
    if isinstance(value, Property):
      references = [value]
      value = value.get()
    else:
      references = []
    for adapter in self._value_adapters:
      value = adapter(value, references)  # type: ignore
    if self._base_type is not None:
      beartype_check(self._base_type, value)
    self._value = value
    self._references = references

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
  def references(self) -> list['Property']:
    return self._references


class NoValueError(Exception):
  pass


class _PropertyGenericAlias(_GenericAlias, _root=True):  # type: ignore
  """
  Special implementation of {@link typing._GenericAlias} for the {@link Property} class such that it
  captures the type argument and passes it to the `base_type` argument of the Property constructor.
  """

  def __call__(self, *args, **kwargs) -> Property:
    return self.__origin__(*args, **kwargs, base_type=self.__args__[0])
