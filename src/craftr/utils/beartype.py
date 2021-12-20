
import typing as t
import types
import beartype

TypeHint = object
_registry: dict[TypeHint, t.Callable] = {}


def beartype_check(value: object, type_hint: TypeHint) -> None:
  """
  Validates the given *value* using the {@link beartype} module and the specified type hint.
  """

  beartype_validator(type_hint)(value)


def beartype_validator(type_hint: TypeHint) -> t.Callable[[object], None]:
  """
  Creates a function that acts as a validator for values and the specified type hint.
  """

  validator = _registry.get(type_hint)

  if validator is None:
    @beartype.beartype
    def _validator(value: type_hint) -> None: ...  # type: ignore
    _registry[type_hint] = validator = _validator

  return validator
