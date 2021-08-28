
import os
import typing as t
from dataclasses import dataclass
from pathlib import Path

from .action import Action, ActionContext


@dataclass
class WriteFileAction(Action):

  #: The path of the file to write to.
  file_path: Path

  #: The contents of the file as text.
  text: t.Optional[str] = None

  #: The encoding if #text is provided.
  encoding: t.Optional[str] = None

  #: The contents of the file to write as binary data.
  data: t.Optional[bytes] = None

  def execute(self, context: ActionContext) -> None:
    os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
    if self.text is not None and self.data is not None:
      raise RuntimeError('both text and data supplied')
    if self.text is not None:
      with open(self.file_path, 'w', encoding=self.encoding) as fpt:
        fpt.write(self.text)
    elif self.data is not None:
      with open(self.file_path, 'wb') as fpb:
        fpb.write(self.data)
    else:
      raise RuntimeError('no text or data supplied')
