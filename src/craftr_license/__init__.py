
from craftr.core import ExtensionRegistry

registry = ExtensionRegistry(__name__)
registry.register('license', lambda p: lambda _: None)
