
import types
import typing as t
import weakref

from nr.preconditions import check_not_none


class WeakInstanceMethod:

  def __init__(self, method: t.Union[types.MethodType, t.Any]) -> None:
    assert isinstance(method, types.MethodType), type(method)
    self._obj = weakref.ref(method.__self__)
    self._func = method.__func__

  def __repr__(self) -> str:
    return f'WeakInstanceMethod(obj={self._obj()!r}, func={self._func!r})'

  def __call__(self, *args, **kwargs) -> None:
    return self._func(check_not_none(self._obj(), 'lost reference to object'), *args, **kwargs)
