
import abc
import types
import typing as t
from craftr.core.property.typechecking import TypeCheckingContext, check_type

from nr.preconditions import check_instance_of

T = t.TypeVar('T')
U = t.TypeVar('U')
V = t.TypeVar('V')
R = t.TypeVar('R')


@t.runtime_checkable
class _IHasClosure(t.Protocol):
  __closure__: t.Tuple


def _add_operator(left: t.Any, right: t.Any) -> t.Any:
  """
  Implements the addition behaviour for properties.
  """

  if isinstance(left, t.Sequence) and right is None:
    return left
  elif isinstance(right, t.Sequence) and left is None:
    return right
  elif not isinstance(left, str) and isinstance(left, t.Sequence) and isinstance(right, t.Sequence):
    return list(left) + list(right)
  return left + right


def _visit_nested(val: t.Any, callback: t.Callable[[t.Any], None]) -> None:
  callback(val)
  if isinstance(val, t.Sequence) and not isinstance(val, (str, bytes, memoryview, bytearray)):
    for item in val:
      _visit_nested(item, callback)
  elif isinstance(val, t.Mapping):
    for value in val.values():
      _visit_nested(value, callback)


class NoValueError(Exception):
  """ Raised when a provider has no value. """


class Provider(t.Generic[T], metaclass=abc.ABCMeta):

  def _get_internal(self) -> t.Optional['Provider[T]']:
    return self

  @abc.abstractmethod
  def get(self) -> T:
    """ Get the value of the propery, or raise a #NoValueError. """

  def or_else(self, default: U) -> t.Union[T, U]:
    """ Get the value of the property, or return *default*. """

    try:
      return self.get()
    except NoValueError:
      return default

  def or_else_get(self, default_supplier: t.Callable[[], U]) -> t.Union[T, U]:
    """ Get the value of the property, or return the value returned by *default_supplier*. """

    try:
      return self.get()
    except NoValueError:
      return default_supplier()

  def or_none(self) -> t.Optional[T]:
    """ Get the value of the property, or return None. """

    return self.or_else(None)

  def visit(self, func: t.Callable[['Provider'], bool]) -> None:
    func(self)

  def __add__(self, other: t.Union[T, 'Provider[T]']) -> 'Provider[T]':
    left = self._get_internal()
    if left is not None:
      return BinaryProvider(_add_operator, left, Provider.of(other))
    return Provider.of(other)

  def __radd__(self, other: t.Union[T, 'Provider[T]']) -> 'Provider[T]':
    right = self._get_internal()
    if right is not None:
      return BinaryProvider(_add_operator, Provider.of(other), right)
    return Provider.of(other)

  def __iadd__(self, other: t.Union[T, 'Provider[T]']) -> 'Provider[T]':
    left = self._get_internal()
    if left is not None:
      return BinaryProvider(_add_operator, left, Provider.of(other))
    return Provider.of(other)

  @staticmethod
  def of(value: t.Union[T, 'Provider[T]']) -> 'Provider[T]':
    if not isinstance(value, Provider):
      return Box(value)
    return value

  def map(self, func: t.Callable[[T], R]) -> 'Provider[R]':
    return MappedProvider(func, self)

  def flatmap(self: 'Provider[t.Collection[T]]', func: t.Callable[[T], t.Collection[R]]) -> 'Provider[t.Collection[R]]':
    return FlatMappedProvider(func, self)


class Box(Provider[T]):

  def __init__(self, value: t.Union[t.Callable[[], T], Provider[T], T, None]) -> None:
    self._value = value

  def get(self) -> T:
    if self._value is None:
      raise NoValueError
    if callable(self._value):
      return self._value()
    if isinstance(self._value, Provider):
      return self._value.get()
    return self._value

  def visit(self, func: t.Callable[['Provider'], bool]) -> None:
    if not func(self):
      return
    if callable(self._value):
      # Check if the closure captures any properies.
      assert isinstance(self._value, _IHasClosure)
      for cell in (self._value.__closure__ or []):
        if isinstance(cell.cell_contents, Provider):
          cell.cell_contents.visit(func)
      value = self._value()
    else:
      value = self._value
    def callback(val: t.Any) -> None:
      if isinstance(val, Provider):
        func(val)
    _visit_nested(value, callback)


def visit_captured_providers(subject: t.Callable, func: t.Callable[[Provider], bool]) -> None:
  assert isinstance(subject, (types.FunctionType, types.MethodType)), type(subject)
  assert isinstance(subject, _IHasClosure)
  for cell in (subject.__closure__ or []):
    if isinstance(cell.cell_contents, Provider):
      cell.cell_contents.visit(func)


class UnaryProvider(Provider[T]):

  def __init__(self, func: t.Callable[[t.Optional[U]], t.Optional[T]], inner: Provider[U]) -> None:
    check_instance_of(inner, Provider)  # type: ignore  # python/mypy#5374
    self._func = func
    self._inner = inner

  def get(self) -> T:
    value = self._func(self._inner.or_none())
    if value is None:
      raise NoValueError
    return value

  def visit(self, func: t.Callable[[Provider], bool]) -> None:
    if func(self):
      self._inner.visit(func)
      visit_captured_providers(self._func, func)


class BinaryProvider(Provider[T]):

  def __init__(self,
    func: t.Callable[[t.Optional[U], t.Optional[V]], T],
    left: Provider[U],
    right: Provider[V],
  ) -> None:
    check_instance_of(left, Provider)  # type: ignore  # python/mypy#5374
    check_instance_of(right, Provider)  # type: ignore  # python/mypy#5374
    self._func = func
    self._left = left
    self._right = right

  def get(self) -> T:
    value = self._func(self._left.or_none(), self._right.or_none())
    if value is None:
      raise NoValueError
    return value

  def visit(self, func: t.Callable[[Provider], bool]) -> None:
    if func(self):
      self._left.visit(func)
      self._right.visit(func)
      visit_captured_providers(self._func, func)


class MappedProvider(Provider[R]):

  def __init__(self, func: t.Callable[[T], R], sub: Provider[T]) -> None:
    self._func = func
    self._sub = sub

  def __repr__(self) -> str:
    return f'MappedProvider({self._func!r}, {self._sub!r})'

  def __bool__(self) -> bool:
    return bool(self._sub)

  def get(self) -> R:
    return self._func(self._sub.get())

  def visit(self, visitor: t.Callable[[Provider], bool]) -> None:
    if visitor(self):
      self._sub.visit(visitor)
      # Check if the closure captures any properies.
      assert isinstance(self._func, _IHasClosure)
      for cell in (self._func.__closure__ or []):
        if isinstance(cell.cell_contents, Provider):
          cell.cell_contents.visit(visitor)


class FlatMappedProvider(Provider[t.Collection[R]]):

  def __init__(self, func: t.Callable[[T], t.Collection[R]], sub: Provider[t.Collection[T]]) -> None:
    self._func = func
    self._sub = sub

  def __repr__(self) -> str:
    return f'FlatMappedProvider({self._func!r}, {self._sub!r})'

  def __bool__(self) -> bool:
    value = self._sub.or_none()
    if value is None:
      return False
    return bool(value)

  def get(self) -> t.Collection[R]:
    value = self._sub.get()
    it = map(self._func, value)
    return type(value)(it)  # type: ignore

  def visit(self, visitor: t.Callable[[Provider], bool]) -> None:
    if visitor(self):
      self._sub.visit(visitor)
      # Check if the closure captures any properies.
      assert isinstance(self._func, _IHasClosure), self._func
      for cell in (self._func.__closure__ or []):
        if isinstance(cell.cell_contents, Provider):
          cell.cell_contents.visit(visitor)
