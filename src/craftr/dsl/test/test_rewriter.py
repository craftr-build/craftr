

from pathlib import Path

import pytest

from .._rewriter import Rewriter, SyntaxError
from .utils.testcaseparser import CaseData, cases_from


@cases_from(Path(__file__).parent / 'rewriter_testcases', can_have_outputs=False)
def test_parser(case_data: CaseData) -> None:
  print('='*30)
  print(case_data.input)
  print('='*30)
  print(case_data.expects)
  print('='*30)

  rewriter = Rewriter(case_data.input, case_data.filename)
  if case_data.expects_syntax_error:
    with pytest.raises(SyntaxError) as excinfo:
      print(rewriter.rewrite().code)
      print('='*30, 'REWRITE RESULT')
    print(excinfo.value.get_text_hint())
    print('='*30, 'ERROR')
    assert excinfo.value.get_text_hint() == case_data.expects
  else:
    result = rewriter.rewrite().code
    print(result)
    print('='*30, 'REWRITE RESULT')
    assert result == case_data.expects
