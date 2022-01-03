import typing as t

import beartype
import typing_extensions as te

T = t.TypeVar('T')
TypeHint = type[T]
_registry: dict[TypeHint, t.Callable] = {}


@t.overload
def check_type(type_hint: TypeHint, value: t.Any) -> te.TypeGuard[T]:
  ...


@t.overload
def check_type(type_hint: object, value: t.Any) -> bool:
  ...


def check_type(type_hint, value):
  """
  Validates the given *value* using the {@link beartype} module and the specified type hint.
  """

  return get_type_checker(type_hint)(value)


@t.overload
def get_type_checker(type_hint: TypeHint) -> t.Callable[[t.Any], te.TypeGuard[T]]:
  ...


@t.overload
def get_type_checker(type_hint: object) -> t.Callable[[t.Any], bool]:
  ...


def get_type_checker(type_hint):
  """
  Creates a function that acts as a validator for values and the specified type hint.
  """

  validator = _registry.get(type_hint)

  if validator is None:

    @beartype.beartype
    def _validator(value: type_hint):
      pass

    def _wrapper(value: TypeHint) -> te.TypeGuard[T]:
      _validator(value)
      return True

    _registry[type_hint] = validator = _wrapper

  return validator
