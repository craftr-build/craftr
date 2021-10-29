
"""
Helpers for added runtime capabilities of transpiled Craftr DSL code, specifically around variable
name resolution when enabling #TranspileOptions.closure_target.
"""

import builtins
import functools
import sys
import types
import typing as t
# import weakref

from craftr.dsl.transpiler import TranspileOptions, transpile_to_ast

undefined = object()


class Context(t.Protocol):
  """
  Protocol for context providers. Context methods are expected to raise a #NameError in case of
  a name resolution error.
  """

  def __getitem__(self, key: str) -> t.Any: ...

  def __setitem__(self, key: str, value: t.Any) -> None: ...

  def __delitem__(self, key: str) -> None: ...


class ObjectContext(Context):
  """
  Looks up names that exist in a wrapped object. Only sets or deletes them if they exist, otherwise
  raises a #NameError. It prevents you from overwriting methods.
  """

  def __init__(self, target: t.Any) -> None:
    self._target = target

  def _error(self, key: str) -> NameError:
    raise NameError(f'object of type {type(self._target).__name__} does not have an attribute {key!r}')

  def __getitem__(self, key: str) -> t.Any:
    value = getattr(self._target, key, undefined)
    if value is not undefined:
      return value
    raise self._error(key)

  def __setitem__(self, key: str, value: t.Any) -> None:
    current = getattr(self._target, key, undefined)
    if current is undefined:
      raise self._error(key)
    if isinstance(current, types.MethodType):
      raise RuntimeError(f'cannot override method {type(self._target).__name__}.{key}()')
    setattr(self._target, key, value)

  def __delitem__(self, key: str) -> None:
    current = getattr(self._target, key, undefined)
    if current is undefined:
      raise self._error(key)
    if isinstance(current, types.MethodType):
      raise RuntimeError(f'cannot delete method {type(self._target).__name__}.{key}()')
    delattr(self._target, key)


class MapContext(Context):
  """
  Similar to #ObjectContext, but acts on a mapping instead.
  """

  def __init__(self, target: t.MutableMapping, description: str) -> None:
    self._target = target
    self._description = description

  def _error(self, key: str) -> NameError:
    raise NameError(f'{self._description} does not have an attribute {key!r}')

  def __getitem__(self, key: str) -> t.Any:
    if key in self._target:
      return self._target[key]
    raise self._error(key)

  def __setitem__(self, key: str, value: t.Any) -> None:
    if key in self._target:
      self._target[key] = value
    else:
      raise self._error(key)

  def __delitem__(self, key: str) -> None:
    if key in self._target:
      del self._target[key]
    else:
      raise self._error(key)


class ChainContext(Context):
  """
  Chain multiple #Context implementations.
  """

  def __init__(self, *contexts: Context) -> None:
    self._contexts = contexts

  def __getitem__(self, key):
    for ctx in self._contexts:
      try:
        return ctx[key]
      except NameError:
        pass
    raise NameError(key)

  def __setitem__(self, key, value):
    for ctx in self._contexts:
      try:
        ctx[key] = value
        return
      except NameError:
        pass
    raise NameError(key)

  def __delitem__(self, key):
    for ctx in self._contexts:
      try:
        del ctx[key]
        return
      except NameError:
        pass
    raise NameError(key)


class Closure(Context):
  r"""
  This class serves as a mapping to use for dynamic name lookup when transpiling Craftr DSL code to Python.
  Several options in the #TranspileOptions need to be tweaked for this to work correctly as the closure
  hierarchy needs to be built up manually:

  * Set #TranspileOptions.closure_target to `__closure__`
  * Set #TranspileOptions.closure_def_prefix to `@__closure__.child\n`
  * Set #TranspileOptions.closure_arglist_prefix to `__closure__,`

  You can initialize a #TranspileOptions object with these values using #init_options().

  When resolving names using #__getitem__(), #__setitem__() and #__delitem__(), the names will be looked
  up in the hierarchy of the closure itself. However do note that #__setitem__() and #__delitem__() cannot
  apply changes to the locals in a function. This is handled by proper rewriting rules in the #NameRewriter.
  """

  @staticmethod
  def init_options(options: TranspileOptions) -> None:
    options.closure_target = '__closure__'
    options.closure_def_prefix = '@__closure__.child\n'
    options.closure_arglist_prefix = '__closure__,'

  @staticmethod
  def get_options() -> TranspileOptions:
    options = TranspileOptions()
    Closure.init_options(options)
    return options

  def __init__(
    self,
    parent: t.Optional['Closure'],
    frame: t.Optional[types.FrameType],
    target: t.Any,
    context_factory: t.Callable[[t.Any], Context] = ObjectContext,
  ) -> None:
    self._parent = parent
    self._frame = frame  # weakref.ref(frame) if frame else None
    self._target = target
    self._target_context = context_factory(target) if target is not None else None
    self._context_factory = context_factory

  @property
  def frame(self) -> t.Optional[types.FrameType]:
    return self._frame
    # if self._frame is None:
    #   return None
    # frame = self._frame()
    # if frame is None:
    #   raise RuntimeError(f'lost reference to closure frame')
    # return frame

  def child(self, func: t.Callable, frame: t.Optional[types.FrameType] = None) -> t.Callable:

    if frame is None:
      frame = sys._getframe(1)
    closure = Closure(self, frame, None, self._context_factory)
    del frame

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
      __closure__ = Closure(self, closure.frame, args[0], self._context_factory) if args else closure
      return func(__closure__, *args, **kwargs)

    return _wrapper

  def run_code(
    self,
    code: str,
    filename: str = '<string>',
    options: t.Optional[TranspileOptions] = None,
    scope: t.Optional[t.Dict[str, t.Any]] = None,
  ) -> None:
    """
    Executes the given Craftr DSL *code* with the #Closure as it's entry `__closure__` object.
    """

    if options:
      Closure.init_options(options)
    else:
      options = Closure.get_options()
    module = compile(transpile_to_ast(code, filename, options), filename, 'exec')
    if scope is None:
      scope = {}
    assert options.closure_target
    scope[options.closure_target] = self
    exec(module, scope)

  def __getitem__(self, key: str) -> t.Any:
    frame = self.frame
    if frame and key in frame.f_locals:
      return frame.f_locals[key]
    if self._target_context is not None:
      try:
        return self._target_context[key]
      except NameError:
        pass
    if self._parent is not None:
      try:
        return self._parent[key]
      except NameError:
        pass
    if hasattr(builtins, key):
      return getattr(builtins, key)
    raise NameError(key)

  def __setitem__(self, key: str, value: t.Any) -> None:
    frame = self.frame
    if frame and key in frame.f_locals:
      raise RuntimeError(f'cannot set local variable through context, this should be handled by the transpiler')
    if self._target_context is not None:
      try:
        self._target_context[key] = value
        return
      except NameError:
        pass
    if self._parent is not None:
      try:
        self._parent[key] = value
        return
      except NameError:
        pass
    raise NameError(f'unclear where to set {key!r}')

  def __delitem__(self, key: str) -> None:
    frame = self.frame
    if frame and key in frame.f_locals:
      raise RuntimeError(f'cannot delete local variable through context, this should be handled by the transpiler')
    if self._target_context is not None:
      try:
        del self._target_context[key]
        return
      except NameError:
        pass
    if self._parent is not None:
      try:
        del self._parent[key]
        return
      except NameError:
        pass
    raise NameError(f'unclear where to delete {key!r}')
