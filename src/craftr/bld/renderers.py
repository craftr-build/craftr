from craftr.core import Action, ActionContext, PathProperty, Property, Task


class FileRendererTask(Action, Task):

  output_file = PathProperty.output()
  contents: Property[str]

  def get_file_contents(self) -> str:
    if self.contents.is_set():
      return self.contents.get()
    raise NotImplementedError

  def is_outdated(self) -> bool:
    fp = self.output_file.get()
    if not fp.exists():
      return True
    return fp.read_text() != self.get_file_contents()

  def execute(self, ctx: ActionContext) -> None:
    self.output_file.get().write_text(self.get_file_contents())
