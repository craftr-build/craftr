
import dataclasses
import typing as t
from craftr.core.base import Action, ActionContext


@dataclasses.dataclass
class LambdaAction(Action):

  delegate: t.Callable[[ActionContext], None]

  def execute(self, context: ActionContext) -> None:
    self.delegate(context)
