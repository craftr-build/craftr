
from textwrap import dedent
from .testcaseparser import CaseData, parse_testcase_file


def test_testcaseparser():
  content = dedent('''
    === TEST abc ===
    foo bar
    === EXPECTS ===
    baz
    === OUTPUTS ===
    spam
    === END ===
  ''')

  result = list(parse_testcase_file(content, '<string>', True))

  assert result == [
    CaseData('<string>', 'abc', 'foo bar', 2, 'baz', 4, False, 'spam', 6)
  ]
