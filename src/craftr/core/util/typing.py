
import typing as t
import typing_extensions as te
import sys


def get_type_hints(obj: t.Any) -> t.Dict[str, t.Any]:
  kwargs = {} if sys.version_info < (3, 9) else {'include_extras': True}
  return t.get_type_hints(obj, **kwargs)  # type: ignore


def _filter_typevars(args: t.Iterable[t.Any]) -> t.List[t.Any]:
  return [x for x in args if not isinstance(x, t.TypeVar)]


def unpack_type_hint(hint: t.Any) -> t.Tuple[t.Optional[t.Any], t.List[t.Any]]:
  """
  Unpacks a type hint into it's origin type and parameters.
  """

  if isinstance(hint, te._AnnotatedAlias):  # type: ignore
    return te.Annotated, _filter_typevars((hint.__origin__,) + hint.__metadata__)  # type: ignore

  if isinstance(hint, t._GenericAlias):  # type: ignore
    return hint.__origin__, _filter_typevars(hint.__args__)

  if hasattr(t, '_SpecialGenericAlias') and isinstance(hint, t._SpecialGenericAlias):  # type: ignore
    return hint.__origin__, []

  if isinstance(hint, type):
    return hint, []

  if isinstance(hint, t._SpecialForm):
    return hint, []

  if isinstance(hint, t.TypeVar):
    return hint, []

  return None, []
