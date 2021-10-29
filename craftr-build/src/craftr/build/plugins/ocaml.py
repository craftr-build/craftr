
"""
Provides a simple interface to building OCaml applications.
"""

import os
from pathlib import Path
import typing as t
import typing_extensions as te

from craftr.core import Project, Property, DefaultTask, Namespace
from craftr.core.actions import CreateDirectoryAction, CommandAction
from craftr.core.actions.action import Action



T = t.TypeVar('T')


class Prop(t.Generic[T]):

  def __init__(self, input: bool = False, output: bool = False) -> None:
    self.input = input
    self.output = output

  def __class_getitem__(self, params):
    if isinstance(params, tuple):
      raise TypeError(f'Prop can only have one type parameter')
    return _PropFactory(params)


class _PropFactory:
  def __init__(self, param) -> None:
    self._param = param
  def __call__(self, *args, **kwargs):
    prop: Prop = Prop(*args, **kwargs)
    prop.hint = self._param
    return prop


class OcamlApplicationTask(DefaultTask):

  output_file = Prop[Path](output=True)
  srcs = Prop[t.List[Path]](input=True)

  #output_file: te.Annotated[Property[Path], DefaultTask.Output]
  #srcs: te.Annotated[Property[t.List[Path]], DefaultTask.InputFile]
  standalone: Property[bool]

  # Properties that construct the output filename.
  output_directory: Property[Path]
  product_name: Property[str]
  suffix: Property[str]

  def init(self) -> None:
    self.standalone.set_default(lambda: False)
    self.output_directory.set_default(lambda: self.project.build_directory / 'ocaml' / self.name)
    self.product_name.set_default(lambda: 'main')
    self.suffix.set_default(lambda: '.exe' if (self.standalone.get() and os.name == 'nt') else '' if self.standalone.get() else '.cma')
    self.output_file.set_default(lambda: self.output_directory.get() / (self.product_name.get() + self.suffix.get()))

    self.run = self.project.task(self.name + 'Run')
    self.run.group = 'run'
    self.run.default = False
    self.run.depends_on(self)

  def finalize(self) -> None:
    super().finalize()
    self.run.do_last(CommandAction([str(self.output_file.get())]))

  def get_actions(self) -> t.List['Action']:
    command = ['ocamlopt' if self.standalone.get() else 'ocamlc']
    command += ['-o'] + [str(self.output_file.get())] + list(map(str, self.srcs.get()))

    # TODO(nrosenstein): Add cleanup action to remove .cmi/cmx/.o files?
    #   There doesn't seem to be an option in the Ocaml compiler to change their
    #   output location.

    return [
      CreateDirectoryAction(self.output_file.get().parent),
      CommandAction(command),
    ]


def apply(project: Project, namespace: Namespace) -> None:
  namespace.add('OcamlApplicationTask', OcamlApplicationTask)
  namespace.add_task_factory('ocamlApplication', OcamlApplicationTask)
