
from types import SimpleNamespace
import pytest
from craftr.dsl.transpiler import transpile_to_source
from craftr.dsl.runtime import Closure

code = """
task "foobar" do: {
  return n_times
}

task "belzebub" do: {
  def n_times = 1
  return n_times
}

task "cheeky" do: {
  def n_times = 1
  return (() -> n_times )()
}
"""


class Project:

  def __init__(self):
    self.tasks = {}

  def task(self, name, *, do):
    self.tasks[name] = do

  n_times = 10


def test_closure():
  print(transpile_to_source(code, '<string>', Closure.get_options()))

  project = Project()
  Closure(None, None, project).run_code(code)

  assert 'foobar' in project.tasks, project.tasks.keys()
  assert project.tasks['foobar'](SimpleNamespace(n_times=3)) == 3
  assert project.tasks['foobar'](SimpleNamespace()) == 10

  assert 'belzebub' in project.tasks, project.tasks.keys()
  assert project.tasks['belzebub'](SimpleNamespace(n_times=3)) == 1
  assert project.tasks['belzebub'](SimpleNamespace()) == 1

  assert 'cheeky' in project.tasks, project.tasks.keys()
  assert project.tasks['cheeky'](SimpleNamespace(n_times=3)) == 1
  assert project.tasks['cheeky'](SimpleNamespace()) == 1


def test_closure_bad_delete():
  with pytest.raises(NameError) as excinfo:
    Closure(None, None, None).run_code('del foobar', '<string>')
  assert str(excinfo.value) == "unclear where to delete 'foobar'"
