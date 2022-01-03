from ._settings import Settings


def test_settings():
  settings = Settings.of({'a': '42', 'b': 'foo;bar;baz', 'c': 'true'})
  assert settings.get_int('a', 0) == 42
  assert settings.get('c', '') == 'true'
  assert settings.get_bool('c', False) == True
