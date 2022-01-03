import argparse
import pdb
import sys
from pathlib import Path

from .core import BuildError, Context, Settings

parser = argparse.ArgumentParser()
parser.add_argument(
  '-O', '--option', default=[], action='append', help='Set or override an option in the settings of the build.'
)
parser.add_argument(
  '--settings-file',
  default=Context.CRAFTR_SETTINGS_FILE,
  type=Path,
  help='Point to another settings file. (default: %(default)s)'
)
parser.add_argument('tasks', metavar='task', nargs='*')
parser.add_argument(
  '-x', '--exclude', metavar='task', action='append', help='Exclude the specified task from the build.'
)
parser.add_argument(
  '-v', '--verbose', action='store_true', help='Enable verbose mode (like -Ocraftr.core.verbose=true).'
)
parser.add_argument('-l', '--list', action='store_true', help='List all tasks.')
parser.add_argument('--pdb', action='store_true')


def main():
  args = parser.parse_args()
  try:
    _main(args)
  except:
    if args.pdb:
      pdb.post_mortem()
    raise


def _main(args):
  settings = Settings.from_file(args.settings_file)
  settings.update(Settings.parse(args.option))
  if args.verbose:
    settings.set('craftr.core.verbose', True)
  ctx = Context(Path.cwd(), settings=settings)

  with ctx.localimport:
    ctx.load_project()

    if args.list:
      for task in ctx.root_project.tasks.all():
        print(task.path)
      return

    try:
      ctx.execute(args.tasks or None, args.exclude)
    except BuildError:
      sys.exit(1)


if __name__ == '__main__':
  main()
