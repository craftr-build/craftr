
import enum
import typing as t
import weakref
from pathlib import Path

from nr.preconditions import check_not_none

from craftr.core.util.typing import unpack_type_hint
from .provider import Box, NoValueError, Provider, T, visit_captured_providers


def unpack_nested_providers(value: t.Any) -> t.Any:
  """
  Unpacks elements in dictionaries/lists when they are #Provider instances.
  """

  if isinstance(value, t.Sequence) and not isinstance(value, (str, bytes, bytearray, memoryview)):
    return [unpack_nested_providers(x) for x in value]
  elif isinstance(value, t.Mapping):
    return {k: unpack_nested_providers(v) for k, v in value.items()}
  elif isinstance(value, Provider):
    return value.get()
  return value


def adapt_value_type(value_type: t.Any, value: t.Any) -> t.Any:
  """
  Called when #Property.set() is called with not a real value. Allows to transform the value.
  """

  assert isinstance(value_type, type) or isinstance(value_type, (t._SpecialForm, t._GenericAlias)), repr(value_type)  # type: ignore

  if isinstance(value, str) and isinstance(value_type, type) and issubclass(value_type, enum.Enum):
    # Find the matching enum value, case in-sensitive.
    value_lower = value.lower()
    enum_value = next((v for v in value_type if v.name.lower() == value_lower), None)
    if enum_value is None:
      raise ValueError(f'{value_type.__name__}.{value} does not exist')
    return enum_value

  generic, args = unpack_type_hint(value_type)

  if generic is not None and generic in (t.List, list, t.Set, set) and isinstance(value, t.Iterable):
    if isinstance(value_type, str):
      raise TypeError('expected non-string sequence')
    if isinstance(value_type, t.Mapping):
      raise TypeError('expected a sequence, not mapping')
    constructor = getattr(generic, '__origin__', generic)
    value = constructor(adapt_value_type(args[0], x) for x in value)

  elif generic is not None and generic in (t.Dict, dict, t.Mapping, t.MutableMapping) and isinstance(value, t.Mapping):
    constructor = getattr(generic, '__origin__', generic)
    value = constructor((k, adapt_value_type(args[1], v)) for k, v in value.items())

  elif isinstance(value_type, type) and issubclass(value_type, Path) or generic == t.Union and Path in args:
    value = Path(value)

  elif value_type == str and isinstance(value, Path):
    # Allow paths to be cast to strings automatically.
    value = str(value)

  return value


def collect_properties(provider: t.Union['HavingProperties', Provider]) -> t.List['Property']:
  """
  Collects all #Property objects that are encountered when visiting the specified provider or all properties of a
  #HavingProperties instance.
  """

  result: t.List[Property] = []

  def _append_if_property(provider: Provider) -> bool:
    if isinstance(provider, Property):
      result.append(provider)
    return True

  if isinstance(provider, HavingProperties):
    for prop in provider.get_properties().values():
      prop.visit(_append_if_property)
  elif isinstance(provider, Provider):
    provider.visit(_append_if_property)
    if isinstance(provider, Property) and provider in result:
      result.remove(provider)
  else:
    raise TypeError('expected Provider or HavingProperties instance, '
      f'got {type(provider).__name__}')

  return result


class Property(Provider[T]):
  """
  Properties are mutable providers that sit as attributes on objects of the #HavingProperties base class. The property
  value type hint is passed passed through the factory class that is returned on a subscript of the #Property class.
  Property values may be used to represent a task output. The property carries the information which task produces its
  value. When the property is attached to a task input, it allows Craftr to introduce a dependency. (This is heavily
  inspired by Gradle).

  Properties only support native types. To represent a list of values, use the #ListProperty.

  # Example

  Properties must be used with a class that as #HavingProperties as its base class.

  ```py
  from craftr.core import HavingProperties, ListProperty, Property

  class MyClass(HavingProperties):
    input_file = Property(default='foo')
    output_file = Property[str]()
  ```
  """

  def __init__(
    self,
    type_: t.Optional[t.Type[T]] = None,
    *,
    default: t.Optional[T] = None,
    default_factory: t.Optional[t.Callable[[], T]] = None,
    is_input: bool = False,
    is_output: bool = False,
    name: t.Optional[str] = None,
  ) -> None:

    self.name = name
    self.type = type_ if type_ is not None else type(default) if default is not None else None
    self.default = default
    self.default_factory = default_factory
    self.is_input = is_input
    self.is_output = is_output
    self._value: t.Optional[Provider[T]] = None
    self._finalized = False
    self._finalized_value: t.Optional[Box[T]] = None

    #: The object that owns the property.
    self._owner: t.Optional['weakref.ReferenceType[HavingProperties]'] = None

  def __repr__(self) -> str:
    return f'{type(self).__name__}[{type_repr(self.type)}]({self.fqn!r})'

  @property
  def fqn(self) -> str:
    if self._owner is None:
      return self.name
    return type(self.owner).__name__ + '.' + self.name

  @property
  def owner(self) -> t.Optional['HavingProperties']:
    return check_not_none(self._owner(), 'lost reference to origin') if self._owner is not None else None

  def set(self, value: t.Union[T, t.Callable[[], T], Provider[T]]) -> None:
    if self._finalized:
      raise RuntimeError(f'{self} is finalized')

    if not isinstance(value, Provider):
      if not callable(value):
        value = self._coerce_on_set(value)
      value = Box(value)

    self._value = value

  def _coerce_on_set(self, value: t.Any) -> T:
    return adapt_value_type(self.type, value)

  def _coerce_on_get(self, value: t.Any) -> T:
    return unpack_nested_providers(value)

  def finalize(self) -> None:
    """ Finalize the property. If already finalized, nothing happens. """

    if not self._finalized:
      try:
        self._finalized_value = Box(self.get())
      except NoValueError:
        pass
      self._finalized = True

  def make_instance(self, owner: 'HavingProperties') -> None:
    prop = type(self)(
      type_=self.type,
      default=self.default,
      default_factory=self.default_factory,
      is_input=self.is_input,
      is_output=self.is_output,
      name=self.name)
    prop._owner = weakref.ref(owner)
    return prop

  # Provider

  def _get_internal(self) -> t.Optional['Provider[T]']:
    return self._value

  def get(self) -> T:
    if self._finalized:
      if self._finalized_value:
        raise NoValueError(self.fqn)
      return self._finalized_value.get()

    if self._value is None:
      if self.default is None and self.default_factory is None:
        raise NoValueError(self.fqn)
      if self.default_factory is not None:
        return self.default_factory()
      return self.default

    return self._coerce_on_get(self._value.get())

  def visit(self, func: t.Callable[[Provider], bool]) -> None:
    if func(self):
      if self._value is not None:
        self._value.visit(func)
      elif self.default_factory is not None:
        visit_captured_providers(self.default_factory, func)


class ListProperty(Property[t.List[T]]):
  """
  A property that implements special handling for lists.
  """

  # Property

  def _coerce_on_set(self, value: t.Any) -> T:
    return adapt_value_type(t.List[self.type], value)


class HavingProperties:
  """
  Base for classes that have properties declared as annotations at the class level. Setting
  property values will automatically wrap them in a #Provider if the value is not already one.
  The constructor will take care of initializing the properties.
  """

  def __init_subclass__(cls) -> None:
    cls.__properties: t.Dict[str, Property] = {}

    for key, value in list(vars(cls).items()):
      if isinstance(value, Property):
        value.name = key
        cls.__properties[key] = value
        delattr(cls, key)

  def __init__(self) -> None:
    for key, value in self.__properties.items():
      object.__setattr__(self, key, value.make_instance(self))

  def __setattr__(self, key: str, value: t.Any) -> None:
    if key in self.__properties:
      raise AttributeError(f'Property {key!r} cannot be overriden, use it\'s .set() method to set the value')
    object.__setattr__(self, key, value)

  def get_properties(self) -> t.Dict[str, Property]:
    return self.__properties
