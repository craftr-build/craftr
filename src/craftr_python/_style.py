from craftr.core import Property

from ._base import DefaultPythonExtension
from ._python import python_project_extensions


@python_project_extensions.register('style')
class Style(DefaultPythonExtension):
  """
  Container for Python style settings (such as indent and line length). May be consumed by other plugins,
  but does generate any tasks itself.
  """

  indent = Property[str](default='    ')
  line_length = Property[int](default=80)
