
"""
This package implements the Craftr DSL laguage.
"""

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.6.0'

import typing as t
from .rewrite import SyntaxError
from .transpiler import TranspileOptions, transpile_to_ast, transpile_to_source

__all__ = ['SyntaxError', 'TranspileOptions', 'transpile_to_ast', 'transpile_to_source', 'execute']


def execute(
  code: t.Union[str, t.TextIO],
  filename: t.Optional[str],
  globals: t.Dict[str, t.Any],
  locals: t.Optional[t.Mapping[str, t.Any]] = None,
  options: t.Optional[TranspileOptions] = None,
) -> None:

  if hasattr(code, 'read'):
    code = t.cast(t.TextIO, code).read()
    filename = getattr(code, 'name', None)

  assert isinstance(code, str)
  filename = filename or '<string>'

  ast = transpile_to_ast(code, filename, options)
  compiled_code = compile(ast, filename, 'exec')
  exec(compiled_code, globals, locals or globals)
