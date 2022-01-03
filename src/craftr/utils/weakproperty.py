
import typing as t
import weakref

T = t.TypeVar('T')


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

  def __get__(self, instance: t.Any, owner: t.Any) -> None:
    has_value: t.Optional[weakref.ReferenceType[T]] = getattr(instance, self._name, None)
    if has_value is None:
      raise AttributeError('property value is not set')
    value = has_value()
    if value is None:
      raise RuntimeError('lost weak reference')
    return value
