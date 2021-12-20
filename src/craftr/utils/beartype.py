
import typing as t
import types
import beartype

T = t.TypeVar('T')
TypeHint = object
_registry: dict[TypeHint, t.Callable] = {}


def beartype_check(type_hint: TypeHint, value: T) -> T:
  """
  Validates the given *value* using the {@link beartype} module and the specified type hint.
  """

  return beartype_validator(type_hint)(value)


def beartype_validator(type_hint: TypeHint) -> t.Callable[[T], T]:
  """
  Creates a function that acts as a validator for values and the specified type hint.
  """

  validator = _registry.get(type_hint)

  if validator is None:
    @beartype.beartype
    def _validator(value: type_hint) -> type_hint: return value  # type: ignore
    _registry[type_hint] = validator = _validator

  return validator
