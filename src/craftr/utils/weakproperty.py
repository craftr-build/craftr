
import typing as t
import weakref

T = t.TypeVar('T')
R = t.TypeVar('R', bound='WeakProperty')


class WeakProperty(t.Generic[T]):

  def __init__(self, name: str, once: bool = False) -> None:
    self._name = name
    self._once = once
    self._value: t.Optional[weakref.ReferenceType[T]] = None

  def __set__(self, instance: t.Any, value: T) -> None:
    has_value: t.Optional[weakref.ReferenceType[T]] = getattr(instance, self._name, None)
    if self._once and has_value is not None:
      raise RuntimeError('property can not be set more than once')
    setattr(instance, self._name, weakref.ref(value))

  def __get__(self, instance: t.Any, owner: t.Any) -> T:
    if instance is None:
      raise AttributeError()
    has_value: t.Optional[weakref.ReferenceType[T]] = getattr(instance, self._name, None)
    if has_value is None:
      raise AttributeError('property value is not set')
    value = has_value()
    if value is None:
      raise RuntimeError('lost weak reference')
    return value

  @classmethod
  def at(cls: R, name: str, once: bool = False) -> T:
    return cls(name, once)


class OptionalWeakProperty(WeakProperty[t.Optional[T]]):

  def __set__(self, instance: t.Any, value: T) -> None:
    has_value: t.Optional[weakref.ReferenceType[T]] = getattr(instance, self._name, None)
    if self._once and has_value is not None:
      raise RuntimeError('property can not be set more than once')
    setattr(instance, self._name, weakref.ref(value) if value is not None else None)

  def __get__(self, instance: t.Any, owner: t.Any) -> t.Optional[T]:
    if instance is None:
      raise AttributeError()
    try:
      return super().__get__(instance, owner)
    except AttributeError:
      return None
