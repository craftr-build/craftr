
import dataclasses
import os
import subprocess as sp
import typing as t
from pathlib import Path
from loguru import logger
from craftr.core import Action, ActionContext


@dataclasses.dataclass
class SystemAction(Action):

  command: t.Optional[t.List[str]] = None
  commands: t.List[t.List[str]] = dataclasses.field(default_factory=list)
  cwd: t.Union[str, Path, None] = None
  env: t.Optional[t.Mapping[str, str]] = None
  tty: bool = False

  def execute(self, ctx: ActionContext) -> None:
    commands = self.commands[:]
    if self.command is not None:
      commands = [self.command] + commands

    env = os.environ.copy()
    env.update(self.env or {})
    for command in commands:
      if ctx.verbose:
        logger.info('Executing $ {}', command)
      sp.check_call(command, env=env, cwd=self.cwd, stdin=None if self.tty else sp.DEVNULL)