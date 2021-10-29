
import os
import re
import typing as t
from dataclasses import dataclass
from pathlib import Path
import pytest
from .sectionfileparser import Section, parse_section_file, Type

@dataclass
class CaseData:
  filename: str
  name: str
  input: str
  input_line: int
  expects: str
  expects_line: int
  expects_syntax_error: bool
  outputs: t.Optional[str]
  outputs_line: t.Optional[int]


def parse_testcase_file(content: str, filename: str, can_have_outputs: bool) -> t.Iterator[CaseData]:
  """
  Parses a Craftr DSL parser test case file. Such a file must be of the following form:

  ```
  === TEST <test_name> ===
  <craftr_dsl_code>
  <...>
  === EXPECTS ===
  <generated_python_code>
  <...>
  === END ===
  ```

  Multiple such blocks may be contained in a single file.
  """

  it = parse_section_file(content)
  try:
    while True:
      section = next(it, None)
      if not section:
        break
      if section.type == Type.Body and section.value.isspace():
        continue
      test_section = section
      if test_section.type != Type.Marker or not (m := re.match(r'(DISABLED\s+)?TEST\s+(\w+)$', test_section.value)):
        raise ValueError(f'{filename}: expected TEST section at line {test_section.line}, got {test_section}')
      test_disabled = m.group(1)
      test_name = m.group(2)
      test_body = next(it)
      if test_body.type != Type.Body:
        raise ValueError(f'{filename}: expected TEST section body at line {test_body.line}')
      expects_section = next(it)
      if expects_section.type != Type.Marker or not (m := re.match(r'EXPECTS(\s+SYNTAX ERROR)?$', expects_section.value)):
        raise ValueError(f'{filename}: expected EXPECTS section at line {expects_section.line}, got {expects_section}')
      expects_syntax_error = m.group(1)
      expects_body = next(it)
      if expects_body.type != Type.Body:
        raise ValueError(f'{filename}: expected EXPECTS section body at line {test_body.line}')
      next_section = next(it)
      if next_section.type != Type.Marker or next_section.value not in ('OUTPUTS', 'END'):
        raise ValueError(f'{filename}: expected OUTPUTS|END section at line {next_section.line}, got {next_section}')
      outputs_body: t.Optional[Section] = None
      if next_section.value == 'OUTPUTS' and can_have_outputs:
        outputs_body = next(it)
        if outputs_body.type != Type.Body:
          raise ValueError(f'{filename}: expected OUTPUT section body at line {outputs_body.line}')
        next_section = next(it)
      if next_section.type != Type.Marker or next_section.value != 'END':
        raise ValueError(f'{filename}: expected END section at line {next_section.line}, got {next_section}')
      if not test_disabled:
        yield CaseData(
          filename,
          test_name,
          test_body.value,
          test_body.line,
          expects_body.value,
          expects_body.line,
          bool(expects_syntax_error),
          outputs_body.value if outputs_body else None,
          outputs_body.line if outputs_body else None,
          )
  except StopIteration:
    raise ValueError(f'{filename}: incomplete test case section')


def cases_from(path: Path, can_have_outputs: bool) -> t.Callable[[t.Callable], t.Callable]:
  """
  Decorator for a test function to parametrize it wil the test cases from a directory.
  """

  def _load(path):
    return {t.name: t for t in parse_testcase_file(path.read_text(), str(path), can_have_outputs)}

  test_cases = {}
  for root, dirs, files in os.walk(path):
    for filename in map(Path(root).joinpath, files):
      if filename.suffix == '.txt':
        test_cases[filename] = _load(filename)
  test_parameters = [(path, name) for path, tests in test_cases.items() for name in tests]

  def decorator(func: t.Callable) -> t.Callable:
    @pytest.mark.parametrize('path,name', test_parameters)
    def wrapper(path, name):
      return func(test_cases[path][name])
    wrapper.__name__ = func.__name__
    return wrapper

  return decorator
