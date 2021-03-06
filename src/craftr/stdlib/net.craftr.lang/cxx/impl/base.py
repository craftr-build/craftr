
import {options} from '../build.craftr'
import nr.fs

from craftr.api import *
from craftr.core import build
from craftr.core.template import TemplateCompiler
from dataclasses import dataclass
from typing import List, Dict, Union, Callable
from nr.stream import Stream as stream
from databind.core import datamodel, field


class NamingScheme:
  def __init__(self, data):
    if isinstance(data, str):
      data = {k.lower(): v for k, v in (x.partition('=')[::2] for x in data.split(','))}
    self.data = data
  def __str__(self):
    return 'NamingScheme({!r})'.format(self.to_str())
  def __getitem__(self, key):
    return self.data[key]
  def to_str(self):
    return ','.join('{}={}'.format(k, v) for k, v in self.data.items())
  def with_defaults(self, scheme):
    if not isinstance(scheme, NamingScheme):
      scheme = NamingScheme(scheme)
    return NamingScheme({**scheme.data, **self.data})
  def get(self, key, default=None):
    return self.data.get(key, default)

NamingScheme.WIN = NamingScheme('e=.exe,lp=,ls=.lib,ld=.dll,o=.obj')
NamingScheme.OSX = NamingScheme('e=,lp=lib,ls=.a,ld=.dylib,o=.o')
NamingScheme.LINUX = NamingScheme('e=,lp=lib,ls=.a,ld=.so,o=.o')
NamingScheme.CURRENT = {'win32': NamingScheme.WIN, 'darwin': NamingScheme.OSX}.get(OS.id, NamingScheme.LINUX)

options.add('namingScheme', str, '')
if not options.namingScheme:
  options.namingScheme = NamingScheme.CURRENT.to_str()
options.namingScheme = NamingScheme(options.namingScheme).with_defaults(NamingScheme.CURRENT)


def short_path(x):
  y = path.rel(x, par=True)
  return x if len(x) < len(y) else y


def is_sharedlib(data):
  return data.type == 'library' and data.preferredLinkage == 'shared'


def is_staticlib(data):
  return data.type == 'library' and data.preferredLinkage == 'static'


@datamodel
class Compiler:
  """
  Represents the flags necessary to support the compilation and linking with
  a compiler in Craftr. Flag-information that expects an argument may have a
  `%ARG%` string included which will then be substituted for the argument. If
  it is not present, the argument will be appended to the flags.
  """

  id = None
  name = None
  family = None
  version = None

  id: str
  name: str
  version: str
  arch: str

  executable_suffix: str
  library_prefix: str
  library_shared_suffix: str
  library_static_suffix: str
  object_suffix: str

  compiler_c: List[str]               # Arguments to invoke the C compiler.
  compiler_cpp: List[str]             # Arguments to invoke the C++ compiler.
  compiler_env: Dict[str, str]        # Environment variables for the compiler.
  compiler_out: List[str]             # Specify the compiler object output file.

  c_std: List[str]
  c_stdlib: List[str] = field(default_factory=list)
  cpp_std: List[str]
  cpp_stdlib: List[str] = field(default_factory=list)
  pic_flag: List[str]                 # Flag(s) to enable position independent code.
  debug_flag: List[str]               # Flag(s) to enable debug symbols.
  define_flag: str                    # Flag to define a preprocessor macro.
  include_flag: str                   # Flag to specify include directories.
  expand_flag: List[str]              # Flag(s) to request macro-expanded source.
  warnings_flag: List[str]            # Flag(s) to enable all warnings.
  warnings_as_errors_flag: List[str]  # Flag(s) to turn warnings into errors.
  optimize_none_flag: List[str]
  optimize_speed_flag: List[str]
  optimize_size_flag: List[str]
  optimize_best_flag: List[str]
  enable_exceptions: List[str]
  disable_exceptions: List[str]
  enable_rtti: List[str]
  disable_rtti: List[str]
  force_include: List[str]
  save_temps: List[str]               # Flags to save temporary files during the compilation step.
  depfile_args: List[str] = field(default_factory=list)  # Arguments to enable writing a depfile or producing output for deps_prefix.
  depfile_name: str = None             # The deps filename. Usually, this would contain the variable $out.
  deps_prefix: str = None              # The deps prefix (don't mix with depfile_name).
  use_framework: str = None

  # OpenMP settings.
  compiler_supports_openmp: bool = False
  compiler_enable_openmp: List[str] = None
  linker_enable_openmp: List[str] = None

  linker_c: List[str]                 # Arguments to invoke the linker for C programs.
  linker_cpp: List[str]               # Arguments to invoke the linker for C++/C programs.
  linker_env: Dict[str, str]          # Environment variables for the binary linker.
  linker_out: List[str]               # Specify the linker output file.
  linker_shared: List[str]            # Flag(s) to link a shared library.
  linker_exe: List[str]               # Flag(s) to link an executable binary.
  linker_lib: List[str]
  linker_libpath: List[str]

  # A dictionary for flags {lang: {static: [], dynamic: []}}
  # Non-existing keys will have appropriate default values.
  linker_runtime: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)

  # XXX support MSVC /WHOLEARCHIVE

  archiver: List[str]                 # Arguments to invoke the archiver.
  archiver_env: List[str]             # Environment variables for the archiver.
  archiver_out: List[str]             # Flag(s) to specify the output file.

  executable_suffix = options.namingScheme['e']
  library_prefix = options.namingScheme['lp']
  library_shared_suffix = options.namingScheme['ld']
  library_static_suffix = options.namingScheme['ls']
  object_suffix = options.namingScheme['o']

  @property
  def is32bit(self):
    return '64' not in self.arch

  @property
  def is64bit(self):
    return '64' in self.arch

  def __repr__(self):
    return '<{} name={!r} version={!r}>'.format(type(self).__name__, self.name, self.version)

  def info_string(self):
    return '{} ({}) {} for {}'.format(
      self.name,
      self.id,
      self.version,
      self.arch)

  def expand(self, args, value=None):
    if isinstance(args, str):
      args = [args]
    if value is not None:
      return [x.replace('%ARG%', value) for x in args]
    return list(args)

  # @override
  def init(self):
    """
    Called from CxxTargetHandler.init().
    """

  def translate_target(self, target, data):
    """
    Called to allow the compiler additional translation steps.
    """

  def get_compile_command(self, target, data, lang):
    """
    This method is called to generate a command to build a C or C++ source
    file into an object file. The command must use action variables to
    reference any files used by the command, eg. commonly `${in,src}` and
    `${out,obj}`.

    The default implementation of this method constructs a command based on
    the data members of the #Compiler subclass.
    """

    if data.type not in ('executable', 'library'):
      error('invalid cxx.type: {!r}'.format(data.type))

    # TODO: Keep track of which level in the transitive the dependencies
    #       the define is coming from in order to properly merge it with
    #       the definesForSharedBuild/definesForStaticBuild and so we can
    #       remove any overwritten defines in a proper order.
    defines = list(data.defines)
    if data.type == 'library' and data.preferredLinkage == 'shared':
      defines += list(data.definesForSharedBuild)
    elif data.type == 'library' and data.preferredLinkage == 'static':
      defines += list(data.definesForStaticBuild)
    if data.addDebugDefines:
      defines = (['DEBUG', '_DEBUG'] if BUILD.debug else ['NDEBUG']) + defines

    # Strip any overriding defines (keep the first encountered define
    # from the right, roughly correlating to the transitive dependency order).
    defines_new = []
    defines_set = set()
    for d in reversed(defines):
      v = ''
      if '=' in d:
        d, v = d.partition('=')[::2]
        v = '=' + v
      if d not in defines_set:
        defines_new.append(d + v)
        defines_set.add(d)
      # TODO: Maybe show a warning that a define was ignored?
    defines = defines_new

    def expand_glob(x):
      if nr.fs.isglob(x):
        return [x for x in nr.fs.glob(x) if nr.fs.isdir(x)]
      return [x]
    includes = [short_path(x) for x in stream.concat(
      expand_glob(y) for y in data.includes)]
    flags = list(data.compilerFlags)
    forced_includes = list(data.prefixHeaders)

    if data.enableOpenmp:
      if not self.compiler_supports_openmp:
        print('[WARNING]: Compiler does not support OpenMP')
      else:
        flags += self.compiler_enable_openmp

    command = self.expand(getattr(self, 'compiler_' + lang))
    command.append('${<src}')
    command.extend(self.expand(self.compiler_out, '${@obj}'))

    if data.saveTemps:
      command.extend(self.expand(self.save_temps))

    # c_std, cpp_std
    std_value = getattr(data, lang + 'Std')
    if std_value:
      command.extend(self.expand(getattr(self, lang + '_std'), std_value))
    # c_stdlib, cpp_stdlib
    stdlib_value = getattr(data, lang + 'Stdlib')
    if stdlib_value:
      command.extend(self.expand(getattr(self, lang + '_stdlib'), stdlib_value))

    for include in stream.unique(includes):
      command.extend(self.expand(self.include_flag, include))
    for define in stream.unique(defines):
      command.extend(self.expand(self.define_flag, define))
    command.extend(flags)
    if data.positionIndependentCode is None and data.type == 'library':
      data.positionIndependentCode = True
    if data.positionIndependentCode:
      command += self.expand(self.pic_flag)

    if data.warningLevel == 'all':
      command.extend(self.expand(self.warnings_flag))
    if data.treatWarningsAsErrors:
      command.extend(self.expand(self.warnings_as_errors))
    command.extend(self.expand(self.enable_exceptions if data.enableExceptions else self.disable_exceptions))
    command.extend(self.expand(self.enable_rtti if data.enableRtti else self.disable_rtti))
    if not BUILD.debug:
      command += self.expand(getattr(self, 'optimize_' + (data.optimization or 'best') + '_flag'))
    if BUILD.debug:
      command += self.expand(self.debug_flag)
    if forced_includes:
      command += stream.concat(self.expand(self.force_include, x) for x in forced_includes)

    if self.depfile_args:
      command += self.expand(self.depfile_args)

    return command

  def create_compile_action(self, target, data, action_name, lang, srcs):
    command = self.get_compile_command(target, data, lang)
    op = operator(action_name, commands=[command], environ=self.compiler_env,
                  deps_prefix=self.deps_prefix)

    objdir = path.join(target.build_directory, 'obj')
    for src in srcs:
      bset = BuildSet({'src': src}, {})
      self.add_objects_for_source(target, data, lang, src, bset, objdir)
      obj_file = bset.outputs['obj'][0]
      if self.depfile_name:
        bset.depfile = TemplateCompiler().compile(self.depfile_name).render({}, {'obj': [obj_file]}, {})[0]
      op.add_build_set(bset)

    return op

  def add_objects_for_source(self, target, data, lang, src, buildset, objdir):
    """
    This method is called from #create_compile_action() in order to construct
    the object output filename for the specified C or C++ source file and add
    it to the *buildset*. Additional files may also be added, for example the
    MSVC compiler will add the PDB file.

    The object file must be tagged as `out` and `obj`. Additional output files
    should be tagged with at least `out` and maybe `optional`.
    """

    obj = path.rel(src, target.directory)
    if not path.issub(obj):
      obj = path.rel(src, session.build_directory)
      if not path.issub(obj):
        # Just keep it in the directory that it is in.
        obj = path.abs(src)
    obj = path.setsuffix(path.abs(obj, objdir), self.object_suffix)
    buildset.add_output_files('obj', [obj])

  def get_link_command(self, target, data, lang):
    """
    Similar to #get_compile_command(), this method is called to generate a
    command to link object files to an executable, shared library or static
    library.
    """

    is_archive = False
    is_shared = False

    if data.type == 'library':
      if data.preferredLinkage == 'shared':
        is_shared = True
      elif data.preferredLinkage == 'static':
        is_archive = True
      else:
        assert False, data.preferredLinkage
    elif data.type == 'executable':
      pass
    else:
      assert False, data.type

    if not data.runtimeLibrary:
      data.runtimeLibrary = 'static' if options.staticRuntime else 'dynamic'

    if is_archive:
      command = self.expand(self.archiver)
      command.extend(self.expand(self.archiver_out, '${@product}'))
    else:
      command = self.expand(self.linker_cpp if lang == 'cpp' else self.linker_c)
      command.extend(self.expand(self.linker_out, '${@product}'))
      command.extend(self.expand(self.linker_shared if is_shared else self.linker_exe))

    flags = list(data.linkerFlags)

    if data.enableOpenmp and self.compiler_supports_openmp and not is_staticlib(data):
      flags += self.linker_enable_openmp

    libs = data.systemLibraries

    if not is_staticlib(data):
      runtime = self.linker_runtime.get(lang, {})
      if data.runtimeLibrary == 'static':
        flags += self.expand(runtime.get('static', []))
      else:
        flags += self.expand(runtime.get('dynamic', []))

    if not is_staticlib(data):
      flags += stream.concat([self.expand(self.linker_libpath, x) for x in stream.unique(data.libraryPaths)])
      flags += stream.concat([self.expand(self.linker_lib, x) for x in stream.unique(libs)])
      flags += stream.concat([self.expand(self.use_framework, x) for x in stream.unique(data.frameworks)])

    command = command + ['$<in'] + flags

    # TODO: Tell the compiler to link staticLibraries and dynamicLibraries
    #       statically/dynamically respectively?

    return command

  def get_link_commands(self, target, data, lang):
    command = self.get_link_command(target, data, lang)
    linker_cmd_len = len(self.linker_cpp if lang == 'cpp' else self.linker_c)
    command = build.Command(command, supports_response_file=True,
                            response_args_begin=linker_cmd_len)
    return [command]

  def create_link_action(self, target, data, action_name, lang, object_files):
    commands = self.get_link_commands(target, data, lang)
    input_files = list(object_files)
    if not is_staticlib(data):
      input_files += data.outLinkLibraries + data.staticLibraries + data.dynamicLibraries
    if data.takeInputObjects:
      input_files += data.outObjectFiles
    op = operator(action_name, commands=commands, environ=self.linker_env)
    bset = BuildSet(
      {'in': input_files},
      {'product': data.productFilename})
    self.add_link_outputs(target, data, lang, bset)
    op.add_build_set(bset)
    return op

  def add_link_outputs(self, target, data, lang, buildset):
    if is_staticlib(data):
      properties({'@+cxx.outLinkLibraries': [data.productFilename]}, target=target)

  def nolink(self, target, data, obj):
    """
    Called when the target is not linked and only object files are compiled.
    """

    properties({'@+cxx.outObjectFiles': obj})

  def on_completion(self, target, data):
    pass
