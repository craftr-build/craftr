
import typing as t
from pathlib import Path

from nr.caching.api import KeyDoesNotExist, KeyValueStore

from craftr.core.base import Task
from craftr.core.property import HavingProperties, collect_properties
from craftr.core.impl.DefaultTask import DefaultTask
from craftr.core.util.collections import unique
from craftr.core.util.task_state import calculate_task_hash, unwrap_file_property

TASK_HASH_NAMESPACE = 'task-hashes'


class PropertiesTask(DefaultTask, HavingProperties):
  """
  This task implementation is what is commonly used to implement custom tasks, as it provides capabilities to
  automatically deduce dependencies between tasks via property relationships (see #HavingProperties). If you
  use the property of one task to set the value of another, that first task becomes a dependency of the latter.

  Furthermore, the type of the property can define how the task's properties are handled in respect to its
  up-to-date calculation. E.g. if a property is marked as an output file, the task is considered out-of-date if
  the output file does not exist or if any of the task's input files have been changed since the output file was
  produced.
  """

  @property
  def _kv_namespace(self) -> KeyValueStore:
    return self.project.context.metadata_store.namespace(TASK_HASH_NAMESPACE)

  # Task

  def finalize(self) -> None:
    """
    Called to finalize the task. This is called automatically after the task is configured.
    Properties are finalized in this call. The subclass gets a chance to set any output properties
    that are derived other properties.
    """

    assert not self.finalized

    for prop in self.get_properties().values():
      if not prop.is_output:
        tasks = (t.cast(Task, p.origin) for p in collect_properties(prop) if isinstance(p.origin, Task))
        self.depends_on(*tasks)

    try:
      self.dependencies.remove(self)
    except ValueError:
      pass

    super().finalize()

  def is_outdated(self) -> bool:
    """
    Checks if the task is outdated.
    """

    if self.always_outdated:
      return True

    # Check if any of the output file(s) don't exist.
    for prop in self.get_properties().values():
      if prop.is_output and (files := unwrap_file_property(prop)) is not None:
        print('@@', files)
        if any(not Path(f).exists() for f in files):
          return True

    # TODO(NiklasRosenstein): If the task has no input file properties or does not produce output
    #   files should always be considered as outdated.

    try:
      stored_hash: t.Optional[str] = self._kv_namespace.load(self.path).decode()
    except KeyDoesNotExist:
      stored_hash = None

    hash_value = calculate_task_hash(self)
    return hash_value != stored_hash

  def complete(self) -> None:
    if not self.always_outdated:
      self._kv_namespace.store(self.path, calculate_task_hash(self).encode())
