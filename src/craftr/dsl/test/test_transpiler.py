import contextlib
import io
from pathlib import Path

from .._execute import execute
from .._runtime import Closure
from .._transpiler import transpile_to_source
from .utils.testcaseparser import CaseData, cases_from


@cases_from(Path(__file__).parent / 'transpiler_testcases', can_have_outputs=True)
def test_transpiler(case_data: CaseData) -> None:
  print('=' * 30, case_data.filename, 'TEST')
  print(case_data.input)
  print('=' * 30, 'EXPECTS')
  print(case_data.expects)
  if case_data.outputs is not None:
    print('=' * 30, 'OUTPUTS')
    print(case_data.outputs)

  options = Closure.get_options() if 'enable_closures' in case_data.options else None
  output = transpile_to_source(case_data.input, case_data.filename, options).rstrip()

  print('=' * 30, 'ACTUAL TRANSPILED SOURCED')
  print(output)

  assert output == case_data.expects.rstrip()

  if case_data.outputs is not None:
    fp = io.StringIO()
    with contextlib.redirect_stdout(fp):
      execute(case_data.input, case_data.filename, {}, None, options)

    print('=' * 30, 'ACTUAL OUTPUT')
    print(fp.getvalue())

    assert fp.getvalue().strip() == case_data.outputs.strip()
