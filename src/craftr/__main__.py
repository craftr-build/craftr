
import argparse
from pathlib import Path

from .core import Context, Settings

parser = argparse.ArgumentParser()
parser.add_argument('-O', '--option', default=[], action='append',
  help='Set or override an option in the settings of the build.')
parser.add_argument('--settings-file', default=Context.CRAFTR_SETTINGS_FILE, type=Path,
  help='Point to another settings file. (default: %(default)s)')
parser.add_argument('tasks', metavar='task', nargs='*')
parser.add_argument('-v', '--verbose', action='store_true',
  help='Enable verbose mode (like -Ocraftr.core.verbose=true).')
parser.add_argument('-l', '--list', action='store_true', help='List all tasks.')


def main():
  args = parser.parse_args()

  ctx = Context(settings=Settings.from_file(args.settings_file))
  ctx.settings.update(Settings.parse(args.option))
  if args.verbose:
    ctx.settings.set('craftr.core.verbose', True)

  ctx.load_project(Path.cwd())

  if args.list:
    for task in ctx.root_project.tasks.all():
      print(task.path)
    return

  ctx.execute(args.tasks or None)


if __name__ == '__main__':
  main()
