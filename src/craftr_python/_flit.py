
from typing import Any
from craftr.bld.system import SystemAction
from craftr.core import Extension
from craftr.core.properties import BoolProperty, Property
from ._python import python_project_extensions, PythonProject


@python_project_extensions.register('flit')
class Flit(Extension[PythonProject]):
  """
  Injects Flit configuration values into the pyproject file.
  """

  version = Property[str](default='3.2')
  setup_py = BoolProperty(default=True)
  repository: Property[str]
  test_repository: Property[str]

  def update_pyproject_config(self, config: dict[str, Any]) -> None:
    if not self.enabled.get():
      return
    config['build-system'] = {
      'requires': [f'flit_core >={self.version.get()}'],
      'build-backend': 'flit_core.buildapi',
    }

    dynamic = []
    if not self.ext_parent.version.is_set():
      dynamic.append('version')
    if not self.ext_parent.description.is_set():
      dynamic.append('description')
    if dynamic:
      config.setdefault('project', {})['dynamic'] = dynamic

  def finalize(self) -> None:
    if not self.enabled.get():
      return

    build_args = []
    if self.setup_py.get():
      build_args += ['--setup-py']

    publish_args = build_args[:]
    if self.repository.is_set():
      publish_args += ['--repository', self.repository.get()]

    test_publish_args = build_args[:]
    if self.test_repository.is_set():
      test_publish_args += ['--repository', self.test_repository.get()]

    build_task = self.ext_parent.project.task('build')
    build_task.default = False
    build_task.do(SystemAction(['flit', 'build'] + build_args))
    build_task.depends_on('updatePyproject')
    build_task.depends_on('check', lazy=True)

    publish_task = self.ext_parent.project.task('publish')
    publish_task.default = False
    publish_task.depends_on(build_task)
    publish_task.do_last(SystemAction(['flit', 'publish'] + publish_args))

    if self.test_repository.is_set():
      test_publish_task = self.ext_parent.project.task('testPublish')
      test_publish_task.default = False
      test_publish_task.depends_on(build_task)
      test_publish_task.do_last(SystemAction(['flit', 'publish'] + test_publish_args))
      publish_task.depends_on(test_publish_task)
