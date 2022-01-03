

from craftr.core import ExtensionRegistry, Project

from . import _flit, _isort, _mypy, _pytest
from ._python import PythonProject

registry = ExtensionRegistry[Project](__name__)
registry.register('python', PythonProject)
