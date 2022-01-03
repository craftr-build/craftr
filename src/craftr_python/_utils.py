import typing as t

from craftr.utils.fs import get_file_in_directory


def get_readme_file(directory: str) -> t.Optional[str]:
  """
  Returns the absolute path to the README for this package.
  """

  return get_file_in_directory(
    directory=directory,
    prefix='README.',
    preferred=['README.md', 'README.rst', 'README.txt', 'README'],
    case_sensitive=False
  )
