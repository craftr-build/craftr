
import dataclasses
import os
from pathlib import Path

from craftr.core.base import Action, ActionContext


@dataclasses.dataclass
class CreateDirectoryAction(Action):

  #: The path of the directory to create.
  path: Path

  def execute(self, context: ActionContext) -> None:
    if not os.path.isdir(self.path):
      os.makedirs(self.path, exist_ok=True)
