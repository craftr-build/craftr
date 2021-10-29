
from craftr.core.base import Action, ActionContext


class NoopAction(Action):

  def execute(self, context: ActionContext) -> None:
    pass
