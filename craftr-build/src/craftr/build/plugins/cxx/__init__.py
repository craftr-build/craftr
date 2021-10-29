
"""
Provides the C++ build configuration tools.
"""

import enum
import json
import shlex as sh
import subprocess as sp
import typing as t
from pathlib import Path

import typing_extensions as te

from craftr.core.graph import Graph

from craftr.build.lib import IExecutableProvider, ExecutableInfo, INativeLibProvider, NativeLibInfo
from craftr.core import Action, HavingProperties, Property, ListProperty, Settings, PropertiesTask, Project
from craftr.core.impl.actions.CommandAction import CommandAction
from craftr.core.impl.actions.CreateDirectoryAction import CreateDirectoryAction
from .namingscheme import NamingScheme


class ProductType(enum.Enum):
  OBJECTS = enum.auto()
  EXECUTABLE = enum.auto()
  STATIC_LIBRARY = enum.auto()
  SHARED_LIBRARY = enum.auto()

  @property
  def is_lib(self) -> bool:
    return self in (ProductType.SHARED_LIBRARY, ProductType.STATIC_LIBRARY)


class Language(enum.Enum):
  C = enum.auto()
  CPP = enum.auto()


class Props(HavingProperties):
  """ Base props for building C/C++ libraries or applications. """

  naming_scheme: NamingScheme = NamingScheme.CURRENT
  sources = ListProperty(Path, is_input=True)
  include_paths = ListProperty(Path)
  public_include_paths = ListProperty(Path)
  build_options = ListProperty(str)
  libs = ListProperty(NativeLibInfo)
  language = Property(Language)
  product_name = Property(str)
  produces = Property(ProductType)
  outputs = ListProperty(Path, is_output=True)
  executable = Property(IExecutableProvider, is_output=True)


class CompileTask(PropertiesTask, Props, IExecutableProvider, INativeLibProvider):

  def _get_preferred_output_directory(self) -> Path:
    return self.project.build_directory / self.name

  def _get_executable_name(self) -> str:
    assert self.produces.get() == ProductType.EXECUTABLE, self.produces.get()
    return self.product_name.get() + self.naming_scheme['e']

  def _get_executable_path(self) -> Path:
    return self._get_preferred_output_directory() / self._get_executable_name()

  def _get_library_name(self) -> str:
    assert self.produces.get().is_lib, self.produces.get()
    return self.naming_scheme['lp'] + self.product_name.get() + self.naming_scheme['ls']

  def _get_library_path(self) -> Path:
    return self._get_preferred_output_directory() / self._get_library_name()

  def _get_objects_output_directory(self) -> Path:
    return self._get_preferred_output_directory() / 'obj'

  def _get_objects_paths(self) -> t.List[Path]:
    object_dir = self._get_objects_output_directory()
    return [(object_dir / Path(f).name).with_suffix(self.naming_scheme['o']) for f in self.sources.get()]

  def _detect_language(self, source_file: str) -> Language:
    if source_file.endswith('.cpp') or source_file.endswith('.cc'):
      return Language.CPP
    else:
      return Language.C

  def _get_compiler(self, language: Language) -> str:
    return 'g++' if language == Language.CPP else 'gcc'

  def pkg_config(self, *pkg_names: str, static: bool = True) -> None:
    """
    Retrieves native lib info from the `pkg-config` tool and appends it to the #libs property.
    """

    self.libs.set(self.libs + [pkg_config(pkg_names, static, self.project.context.settings)])

  # IExecutableProvider
  def get_executable_info(self) -> t.Optional[ExecutableInfo]:
    if self.produces.get() == ProductType.EXECUTABLE:
      return ExecutableInfo(str(self._get_executable_path()))
    return None

  # INativeLibProvider
  def get_native_lib_info(self) -> t.Optional[NativeLibInfo]:
    if self.produces.get().is_lib:
      include_paths = list(map(str, self.public_include_paths.or_else_get(lambda: self.include_paths.or_else([]))))
      return NativeLibInfo(name=self.path, library_files=[str(self._get_library_path())], include_paths=include_paths)
    return None

  # Task
  def init(self) -> None:
    self.product_name.default_factory = lambda: self.project.name
    self.produces.set(ProductType.EXECUTABLE)
    self.executable.default_factory = lambda: self

  # Task
  def finalize(self) -> None:
    if not self.finalized:
      if self.produces.get() == ProductType.EXECUTABLE:
        self.outputs.set([self._get_executable_path()])
      elif self.produces.get().is_lib:
        self.outputs.set([self._get_library_path()])
      elif self.produces.get() == ProductType.OBJECTS:
        self.outputs.set(self._get_objects_paths())
      else: assert False, self.produces
    super().finalize()

  # Task
  def get_actions(self, graph: Graph[Action]) -> t.List[Action]:
    # Collect native libs from dependencies.
    # TODO(nrosenstein): Transitive dependencies?
    native_deps: t.List[NativeLibInfo] = self.libs.or_else([])[:]
    for dep in self.get_dependencies():
      if isinstance(dep, INativeLibProvider):
        info = dep.get_native_lib_info()
        if info is not None:
          native_deps.append(info)

    # Collect the include paths.
    include_paths = self.include_paths.or_else([]) + self.public_include_paths.or_else([])

    # Generate the compiler flags.
    flags: t.List[str] = self.build_options.or_else([])[:]
    if self.produces.get() == ProductType.SHARED_LIBRARY:
      flags += ['-shared', '-fPIC']
    for path in include_paths:
      flags.append('-I' + str(path))
    for ndep in native_deps:
      flags += ['-I' + x for x in ndep.include_paths]
      flags += ['-D' + x for x in ndep.defines]

    create_directories = graph.create_sequential_group('create_directories')
    create_directories.add(
      CreateDirectoryAction(self._get_preferred_output_directory()),
      CreateDirectoryAction(self._get_objects_output_directory()))

    compile_object_files = graph.create_group('compile_object_files')
    compile_object_files.depends_on(create_directories)

    # Generate actions to compile object files.
    languages: t.Set[Language] = set()
    object_files = self._get_objects_paths()
    for source_file, object_file in zip(map(str, self.sources.get()), object_files):
      language = self.language.or_else_get(lambda: self._detect_language(source_file))
      compiler = self._get_compiler(language)
      compile_command = [compiler] + flags + ['-c', source_file, '-o', str(object_file)]
      compile_object_files.add(CommandAction(command=compile_command))
      languages.add(language)

    # Generate the archive or link action.
    if self.produces.get() == ProductType.STATIC_LIBRARY:
      archive_command = ['ar', 'rcs', str(self._get_library_path())] + list(map(str, self._get_objects_paths()))
      actions.append(CommandAction(command=archive_command))

    elif self.produces.get() != ProductType.OBJECTS:
      if self.produces.get() == ProductType.EXECUTABLE:
        product_filename = self._get_executable_path()
      elif self.produces.get() == ProductType.SHARED_LIBRARY:
        product_filename = self._get_library_path()
      else: assert False, self.produces.get()
      static_libs = [y for x in native_deps for y in x.library_files]
      for ndep in native_deps:
        flags += ['-L' + x for x in ndep.library_search_paths]
        flags += ['-l' + x for x in ndep.library_names]
      linker_command = [compiler] + flags + list(map(str, object_files)) + static_libs + ['-o', str(product_filename)]
      actions.append(CommandAction(command=linker_command))

    return actions


class PkgConfigError(Exception):
  pass


def pkg_config(pkg_names: t.Sequence[str], static: bool, settings: 'Settings') -> NativeLibInfo:
  """
  This function runs the `pkg-config` command with the specified *pkg_name* and returns the
  library data that can be consumed by the #Compile task.

  The following keys are supported in the JSON file or dictionary mode:

  * includes
  * defines
  * syslibs
  * libpath
  * cflags
  * ldflags
  """

  if isinstance(pkg_names, str):
    pkg_names = [pkg_names]

  includes: t.List[str] = []
  defines: t.List[str] = []
  syslibs: t.List[str] = []
  libpath: t.List[str] = []
  compile_flags: t.List[str] = []
  link_flags: t.List[str] = []
  flags: t.List[str] = []
  skip: t.Set[str] = set()

  # Collect overrides (JSON files configured from settings).
  for pkg in pkg_names:
    override = settings.get('cxx.pkg-config.' + pkg, None)
    if override is None:
      continue
    data: t.Dict[str, t.Any] = {}
    if override.endswith('.json'):
      with open(override) as fp:
        data = json.load(fp)
    else:
      flags += sh.split(override)
    includes += data.get('includes', [])
    defines += data.get('defines', [])
    syslibs += data.get('syslibs', [])
    libpath += data.get('libpath', [])
    compile_flags += data.get('compile_flags', [])
    link_flags += data.get('link_flags', [])

  # Get the remaining package data from pkg-config.
  pkg_names = [x for x in pkg_names if x not in skip]
  if pkg_names:
    command = ['pkg-config'] + pkg_names + ['--cflags', '--libs']
    if static:
      command.append('--static')

    try:
      flags += sh.split(sp.check_output(command).decode())
    except FileNotFoundError as exc:
      raise PkgConfigError('pkg-config is not available ({})'.format(exc))
    except sp.CalledProcessError as exc:
      raise PkgConfigError('{} not installed on this system\n\n{}'.format(
          pkg_names, exc.stderr or exc.stdout))

  # Parse the flags.
  for flag in flags:
    if flag.startswith('-I'):
      includes.append(flag[2:])
    elif flag.startswith('-D'):
      defines.append(flag[2:])
    elif flag.startswith('-l'):
      syslibs.append(flag[2:])
    elif flag.startswith('-L'):
      libpath.append(flag[2:])
    elif flag.startswith('-Wl,'):
      link_flags.append(flag[4:])
    else:
      compile_flags.append(flag)

  return NativeLibInfo(
    name='pkg-config[' + ','.join(pkg_names) + ']',
    include_paths=includes,
    library_files=[],
    library_search_paths=libpath,
    library_names=syslibs,
    defines=defines,
    compiler_flags=compile_flags,
    linker_flags=link_flags)


def apply(project: Project) -> None:
  project.extensions.add('CxxProductType', ProductType)
  project.extensions.add('CxxLanguage', Language)
  project.extensions.add('CxxCompileTask', CompileTask)
  project.extensions.add_task_factory('cxx', CompileTask)
