

import types
import typing as t

from craftr.utils.weakproperty import WeakProperty

from .properties import Configurable

T = t.TypeVar('T')
T_co = t.TypeVar('T_co', covariant=True)
_T_Factory = t.TypeVar('_T_Factory', bound=t.Union[t.Callable[[t.Any], t.Any], t.Type['_FactoryConstructor']])


class _FactoryConstructor(t.Protocol[T_co]):
  def __init__(self, _: T) -> None: ...


class Extension(t.Generic[T], Configurable):
  """
  Represents an object extension that has a {@link finalize()} method that will be called automatically
  by the parent extension object when it itself is finalized. An extension can have extensions itself
  by adding to the {@link ext} namespace.

  In the Craftr DSL, the extensions are accessible through dynamic name resolution without having to go
  through the {@link ext} attribute.
  """

  ext: types.SimpleNamespace
  ext_parent = WeakProperty[T].at('_ext_parent', True)

  def __init__(self, ext_parent: t.Optional[T] = None) -> None:
    super().__init__()
    self.ext = types.SimpleNamespace()
    if ext_parent is not None:
      self.ext_parent = ext_parent

  def finalize(self) -> None:
    for value in vars(self.ext).values():
      if isinstance(value, Extension):
        value.finalize()


class ExtensionRegistry(t.Generic[T]):
  """
  A registry for extension factories that can be added to another {@link Extension} object. Plugin entrypoints
  may point to an instance of this class instead of a function that accepts a {@link Project}.

  Example usage:

  ```py
  from craftr.core import Extension, ExtensionRegistry
  class MyExtension(Extension):
    def __init__(self, project: Project) -> None:
      ...
  registry = ExtensionRegistry[Project]()
  registry.register('my_extension', MyExtension)
  ```
  """

  def __init__(self, name: t.Optional[str] = None) -> None:
    self._name = name
    self._factories: t.Dict[str, t.Callable[[T], t.Any]] = {}

  def __repr__(self) -> str:
    return f'{type(self).__name__}(name={self._name!r})'

  @t.overload
  def register(self, name: str) -> t.Callable[[_T_Factory], _T_Factory]: ...

  @t.overload
  def register(self, name: str, factory: t.Union[t.Callable[[T], t.Any], t.Type[_FactoryConstructor]]) -> None: ...

  def register(self, name, factory=None):
    if factory is None:
      def _decorator(factory):
        assert factory is not None
        self.register(name, factory)
        return factory
      return _decorator
    else:
      if name in self._factories:
        raise ValueError(f'extension factory name {name!r} already used')
      self._factories[name] = factory

  def apply(self, ext: Extension, arg: T) -> None:
    """ Add the contents of the registry to the extension. """

    for key, value in self._factories.items():
      setattr(ext.ext, key, value(arg))
