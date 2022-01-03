

import typing as t

from ._transpiler import TranspileOptions, transpile_to_ast


def execute(
  code: t.Union[str, t.TextIO],
  filename: t.Optional[str],
  globals: t.Dict[str, t.Any],
  locals: t.Optional[t.Mapping[str, t.Any]] = None,
  options: t.Optional[TranspileOptions] = None,
) -> None:
  """
  Executes Craftr DSL code in the context specified with *globals* and *locals*.

  @param code: The code to execute.
  @param filename: The filename where the code is from; shown in errors.
  @param globals: The globals for the code.
  @param locals: The locals for the code.
  @param options: Options for the DSL transpiler.
  """

  if hasattr(code, 'read'):
    code = t.cast(t.TextIO, code).read()
    filename = getattr(code, 'name', None)

  assert isinstance(code, str)
  filename = filename or '<string>'

  ast = transpile_to_ast(code, filename, options)
  compiled_code = compile(ast, filename, 'exec')
  exec(compiled_code, globals, locals or globals)
