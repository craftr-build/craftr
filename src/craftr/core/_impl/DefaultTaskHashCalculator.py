
import hashlib
from pathlib import Path
from ..properties import is_path_property, get_path_property_paths
from .._tasks import TaskHashCalculator, Task


class DefaultTaskHashCalculator(TaskHashCalculator):
  """
  Calculates a hash for the task that represents the state of it's inputs (property values and input file contents).
  That hash is used to determine if the task is up to date with it's previous execution or if it needs to be executed.

  > Implementation detail: Expects that all important information of a property value is
  > included in it's #repr(), and that the #repr() is consistent.
  """

  def __init__(self, hash_algo: str = 'sha1') -> None:
    self._hash_algo = hash_algo

  @staticmethod
  def _hash_file(hasher: 'hashlib._Hash', path: Path) -> None:
    with path.open('rb') as fp:
      while True:
        chunk = fp.read(8048)
        hasher.update(chunk)
        if not chunk:
          break

  def calculate_hash(self, task: Task) -> str:
    hasher = hashlib.new(self._hash_algo)
    encoding = 'utf-8'

    for property in sorted(task.get_properties().values(), key=lambda p: p.name):
      hasher.update(property.name.encode(encoding))
      hasher.update(repr(property.get(None)).encode(encoding))

      if is_path_property(property) and not property.is_output:
        [self._hash_file(hasher, f) for f in get_path_property_paths(property) if f.is_file()]

    return hasher.hexdigest()
