from craftr.core import ExtensionRegistry, Project

registry = ExtensionRegistry[Project](__name__)
registry.register('license', lambda p: lambda _: None)
