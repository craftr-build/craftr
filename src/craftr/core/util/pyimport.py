
import importlib
import typing as t


def load_class(qualname: str) -> t.Type:
  if ':' in qualname:
    module_name, member_name = qualname.rpartition(':')[::2]
  else:
    module_name, member_name = qualname.rpartition('.')[::2]
  try:
    return getattr(importlib.import_module(module_name), member_name)
  except (AttributeError, ModuleNotFoundError, ValueError) as exc:
    raise ModuleNotFoundError(f'unable to load class {qualname!r}: {exc}')
