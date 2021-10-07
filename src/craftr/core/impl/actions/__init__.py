
import typing as t

from craftr.core.base import Action
from craftr.core.exceptions import NoValueError
from craftr.core.project import Project

if t.TYPE_CHECKING:
  from craftr.core.impl.DefaultTask import DefaultTask


def action_as_task(action_cls: t.Type[Action], project: Project, name: str) -> 'DefaultTask':
  """
  Factory function to produce a task that contains exactly the properties of this action through the class annotations.
  The action will be created by passing a keyword argument for every populated property value.
  """

  from craftr.core.impl.DefaultTask import DefaultTask

  # TODO: How can we best identify which properties are inputs and which are outputs?

  class _ActionTask(DefaultTask):
    __annotations__ = {k: Property[v] for k, v in t.get_type_hints(action_cls).items()}  # type: ignore

    def get_actions(self) -> t.List[Action]:
      kwargs: t.Dict[str, t.Any] = {}
      for key, prop in self.get_properties().items():
        try:
          kwargs[key] = prop.get()
        except NoValueError:
          if hasattr(action_cls, key):
            kwargs[key] = getattr(action_cls, key)
          else:
            raise
      return [action_cls(**kwargs)]  # type: ignore

  _ActionTask.__name__ = action_cls.__name__ + 'Task'
  _ActionTask.__qualname__ = _ActionTask.__qualname__.rpartition('.')[0] + '.' + _ActionTask.__name__
  return _ActionTask(project, name)
