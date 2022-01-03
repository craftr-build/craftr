
from craftr.core import ExtensionRegistry, Project
from ._python import PythonProject
from . import _flit, _isort, _mypy, _pytest

registry = ExtensionRegistry[Project](__name__)
registry.register('python', PythonProject)
