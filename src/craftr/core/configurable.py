
import typing as t

T_contra = t.TypeVar('T_contra', contravariant=True)
T_co = t.TypeVar('T_co', covariant=True)
U_co = t.TypeVar('U_co', covariant=True)


@t.runtime_checkable
class Closure(t.Protocol[T_contra, U_co]):

  def __call__(__self, self: T_contra, *arguments: t.Any, **kwarguments: t.Any) -> U_co:
    raise NotImplementedError(f'{type(self).__name__}.__call__() is not implemented')


class Configurable(t.Protocol[T_co, U_co]):
  """
  Abstract base class for objects configurable through closures. Basically they are
  """

  def __call__(self, closure: Closure[T_co, t.Any]) -> U_co:
    raise NotImplementedError(f'{type(self).__name__}.__call__() is not implemented')
