# craftr-core

The `craftr-core` package provides the core build system functions for the Craftr build system.

## Concepts

### Projects

A project is the main unit that is used to represent a collection of tasks. A project has a collection
of tasks and possibly other sub-projects. Every project has a name and unique ID (aka. path) inside the
current build context.

### Tasks

Tasks encapsulate the configuration and logic of an operation in a build. Examples include the compilation
or generation of source files, copying or compressing files. Such operations are usually described using a
sequence of Actions, see below. Dependencies between individual tasks describe a directed acyclic graph used
for determining the order in which tasks need to be executed.

A task has a set of input and output files. If an input files changes or an output file does not exist, a
task is considered outdated and will be executed again. There are also tasks that are not executed by
default unless depended on by another tasks that is executed or explicitly specified as to be executed in
a given execution of the build graph.

### Actions

An action is a concrete unit of work that can be executed as part of a build. A task is usually described
by one or more actions. Dependencies between actions express the order in which they are to be executed
relative to the other actions produced by the same task.

### Plugins

Plugins are reusable pieces of build logic that can be applied to projects. A plugin usually registers
a new task or task factory in the project which is subsequently accessible via the `project.ext` object
or from the namespace object returned by `Project.apply()`.

### Settings

Craftr settings are files in a line-based `key=value` format. There are a bunch of settings that control
the behaviour of the Craftr core components. No settings file is loaded implicitly by the `Context` class.

| Option                         | Default value |
| ------------------------------ | ------------- |
| `core.build_directory`         | `.build`
| `core.executor`                | `craftr.core.executor.default.DefaultExecutor`
| `core.plugin.loader`           | `craftr.core.plugin.default.DefaultPluginLoader`
| `core.plugin.loader.delegates` | `craftr.core.project.loader.default.DefaultProjectLoader,craftr.build.loader.DslProjectLoader?`
| `core.plugin.entrypoint`       | `craftr.plugins`
| `core.project.loader`          | `craftr.core.project.loader.delegate.DelegateProjectLoader`
| `core.verbose`                 | `False`
| `core.task_selector`           | `craftr.core.task.selector.default.DefaultTaskSelector`

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
