
import abc
import copy
import typing as t
import weakref

from craftr.utils.typechecking import check_type, TypeHint
from nr.pylang.utils.singletons import NotSet

A = t.TypeVar('A', covariant=True)
T = t.TypeVar('T')
R = t.TypeVar('R')
T_BaseProperty = t.TypeVar('T_BaseProperty', bound='BaseProperty')
_GenericAlias = t._GenericAlias  # type: ignore


class HasProperties(abc.ABC):
  """
  Base class for classes that have properties declared on the class level. When an instance of the class
  is created, its properties will be copied and bound to the instance.
  """

  __properties__: t.ClassVar[dict[str, 'BaseProperty']] = {}

  def __init_subclass__(cls) -> None:
    cls.__properties__ = {}
    for base in cls.__bases__:
      if issubclass(base, HasProperties):
        cls.__properties__.update(base.__properties__)
    for key, value in cls.__annotations__.items():
      origin = value.__origin__ if isinstance(value, _GenericAlias) else value
      if (isinstance(origin, type) and issubclass(origin, BaseProperty)) and key not in cls.__properties__:
        cls.__properties__[key] = p = value()
        p._name = key
    for key in dir(cls):
      value = getattr(cls, key, None)
      if isinstance(value, BaseProperty):
        assert value._name is None or value._name == key, (key, value)
        value._name = key
        cls.__properties__[key] = value

    # Ensure all properties have names.
    for k, v in cls.__properties__.items(): assert v._name, f'{cls.__name__}.{k}'

  def __init__(self) -> None:
    super().__init__()
    for key, value in self.__properties__.items():
      setattr(self, key, value._bound_copy(self))

  def get_properties(self) -> t.Dict[str, 'BaseProperty']:
    return {k: getattr(self, k) for k in self.__properties__}


class BaseProperty(t.Generic[T, A]):
  """
  The base class for properties on tasks. Properties are the preferred way to make task implementation
  configurable as they make tracking dependencies between tasks easier.

  @generic_param T: The value type that the property holds.
  @generic_param A: The value type that the property accepts and can automatically coerce to {@code T}. This
    can only be different from {@code T} if respective value adapters are registered in the property.

  Note: Use the {@link Property} type alias to refer to a type specialization with a single generic argument
  for both the {@code T} and {@code A} param.
  """

  def __init__(
    self, *,
    default: t.Union[T, A, t.Callable[[], t.Union[T, A]], NotSet] = NotSet.Value,
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
    self._references: list['BaseProperty'] = []
    self._value_adapters: list[t.Callable[[t.Any, list[BaseProperty]], t.Any]] = []
    self.__post_init__()
    if default is not NotSet.Value:
      self.set(self._get_default())

  def __post_init__(self) -> None:
    pass

  def __class_getitem__(cls, type_hint: tuple[type[T], type[A]]) -> type['BaseProperty[T, A]']:
    assert isinstance(type_hint, tuple) and len(type_hint) == 2, repr(type_hint)
    return _BasePropertyGenericAlias(cls, type_hint)  # type: ignore

  def __repr__(self) -> str:
    return f'{type(self).__name__}(name={self._name!r})'

  def __call__(self, value: t.Union[T, A]) -> None:
    self.set(value)

  def _get_default(self) -> t.Union[T, A, NotSet]:
    if self._default is NotSet.Value:
      return NotSet.Value
    if callable(self._default):
      return self._default()
    else:
      return self._default

  def _bound_copy(self: T_BaseProperty, owner: t.Any) -> T_BaseProperty:
    new_self = copy.copy(self)
    new_self._owner = weakref.ref(owner)
    if self._default is not NotSet.Value:
      new_self._value = copy.deepcopy(self._get_default())
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

  def set(self, value: t.Union[T, A, 'BaseProperty[T, t.Any]', 'BaseProperty[A, t.Any]']) -> None:
    if isinstance(value, BaseProperty):
      references = [value]
      value = value.get()
    else:
      references = []
    for adapter in self._value_adapters:
      value = adapter(value, references)  # type: ignore
    if self._base_type is not None:
      check_type(self._base_type, value)
    self._value = t.cast(T, value)
    self._references = references

  @property
  def name(self) -> str:
    assert self._name is not None
    return self._name

  @property
  def owner(self) -> t.Any:
    if self._owner:
      value = self._owner()
      if value is None:
        raise RuntimeError('lost reference to property owner')
      return value
    return None

  @property
  def references(self) -> list['BaseProperty']:
    return self._references


class NoValueError(Exception):
  pass


class _BasePropertyGenericAlias(_GenericAlias, _root=True):  # type: ignore
  """
  Special implementation of {@link typing._GenericAlias} for the {@link BaseProperty} class such that it
  captures the type argument and passes it to the `base_type` argument of the BaseProperty constructor.
  """

  def __call__(self, *args, **kwargs) -> BaseProperty:
    return self.__origin__(*args, **kwargs, base_type=self.__args__[0])


# NOTE (@nrosenstein): We would like to make this an alias instead ({@code Property = BaseProperty[T, T]}), but
#   that will not allow instance checks using the alias in MyPy, even if we could properly implement that check
#   in {@link _BasePropertyGenericAlias}.
class Property(BaseProperty[T, T]):

  def __class_getitem__(cls, type_hint: type[T]) -> type['BaseProperty[T, T]']:  # type: ignore
    return _BasePropertyGenericAlias(cls, (type_hint,))  # type: ignore


class BoolProperty(BaseProperty[bool, bool]):

  def __call__(self, value: bool = True) -> None:
    self.set(value)


class Configurable(HasProperties):
  """
  A base class for objects that are configurable with closures. Every configurable has an "enabled" property
  that will be set to {@code True} the moment that the object is configured with a closure.
  """

  enabled = BoolProperty(default=False)

  def __call__(self: T, closure: t.Callable[[T], t.Any]) -> None:
    if 'enabled' in self.__properties__:
      self.enabled.set(True)
    closure(self)
