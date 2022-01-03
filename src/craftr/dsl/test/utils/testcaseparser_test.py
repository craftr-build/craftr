from textwrap import dedent

from .testcaseparser import CaseData, parse_testcase_file


def test_testcaseparser():
  content = dedent(
    '''
    === OPTION foobar ===
    === TEST abc ===
    foo bar
    === EXPECTS ===
    baz
    === OUTPUTS ===
    spam
    === END ===
  '''
  )

  result = list(parse_testcase_file(content, '<string>', True))

  assert result == [CaseData('<string>', 'abc', 'foo bar', 3, 'baz', 5, False, 'spam', 7, {'foobar'})]
