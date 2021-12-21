
import typing as t
from pathlib import Path

from nr.caching.api import NamespaceStore
from craftr.utils.caching import JsonDirectoryStore
from ._tasks import TaskHashCalculator, DefaultTaskHashCalculator


class Context:

  task_hash_calculator: TaskHashCalculator

  def __init__(self) -> None:
    self.task_hash_calculator = DefaultTaskHashCalculator()
    self._metadata_store: t.Optional[MetadataStore] = None

  @property
  def metadata_store(self) -> 'MetadataStore':
    if self._metadata_store is None:
      path = self.get_default_build_directory(self.root_project) / '.craftr-metadata'
      self._metadata_store = MetadataStore(path)
    return self._metadata_store


class MetadataStore:

  def __init__(self, path: Path) -> None:
    self._store = JsonDirectoryStore(str(path), create_dir=True)

  def load(self, namespace: str, key: str) -> bytes:
    return self._store.namespace(namespace).load(key)

  def store(self, namespace: str, key: str, value: bytes) -> bytes:
    return self._store.namespace(namespace).store(key, value)

