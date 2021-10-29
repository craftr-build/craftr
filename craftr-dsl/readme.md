# craftr-dsl

The Craftr DSL is a transpiler for the Python language that introduces the concept of
**closures**, **function calls without parentheses** and a few other syntactical sugar
into the language. The language is a full superset of Python 3 code. The added syntax
features should only be used where it makes the code more readable or where it is
semantically more relevant.

## Installation

From Pip:

    $ pip install craftr-dsl[codegen,colors]

Latest from GitHub:

    $ pip install git+https://github.com/craftr-build/craftr-dsl

Requirements: Python 3.8 or newer

## Hello, World!

A convoluted Hello, World! example in Craftr DSL might look like this:

```py
# hello.craftr
world = { self('World!') }
world { print('Hello,', self) }
```

This is transpiled to

```py
# $ python -m craftr.dsl hello.craftr -E | grep -v -e '^$'
def _closure_1(self, *arguments, **kwarguments):
    self('World!')
world = _closure_1
def _closure_2(self, *arguments, **kwarguments):
    print('Hello,', self)
world(_closure_2)
```

And evaluates to

```py
# $ python -m craftr.dsl hello.craftr
Hello, World!
```

## Language features

The Craftr DSL grammar and code generator can be configured to an extend to turn some
language features and semantics on and off. What will be shown below in most examples
is compatible with the default configuration unless otherwise noted.

### Closures

Closures are formed with the following syntax: `[ arg -> | (arg1, arg2, ...) -> ] { body }`. A closure without
an argument list automatically has the signature `(self, *argnames, **kwargnames)`.

<table align="center"><tr><th>Craftr DSL</th><th>Python</th></tr>

<tr><td>

```py
filter({ self % 2 }, range(5))
```
</td><td>

```py
def _closure_1(self, *argnames, **kwargnames):
    self % 2
filter(_closure_1, range(5))
```
</td></tr>


<tr><td>

```py
filter(x -> x % 2, range(5))
```
</td><td>

```py
def _closure_1(x):
    return x % 2
filter(_closure_1, range(5))
```
</td></tr>


<tr><td>

```py
reduce((a, b) -> {
  a.append(b * 2)
  return a
}, [1, 2, 3], [])
```
</td><td>

```py
def _closure_1(a, b):
    a.append(b * 2)
    return a
reduce(_closure_1, [1, 2, 3], [])
```
</td></tr>

</table>


### Function calls without parentheses

Such function calls are only supported at the statement level. A function can be called without parentheses by
simply omitting them. Variadic and keyword arguments are supported as expected. Applying a closure on an object
is basically the same as calling that object with the function, and arguments following the closure are still
supported.


<table align="center"><tr><th>Craftr DSL</th><th>Python</th></tr>

<tr><td>

```py
print 'Hello, World!', file=sys.stderr
```
</td><td>

```py
print('Hello, World!', file=sys.stderr)
```
</td></tr>


<tr><td>

```py
map {
  print('Hello,', self)
}, ['John', 'World']
```
</td><td>

```py
def _closure_1(self, *arguments, **kwarguments):
    print('Hello,', self)
map(_closure_1, ['John', 'World'])
```
</td></tr>

</table>


### Unseparated arguments & colon keyword arguments

The Craftr DSL allows passing arguments to function calls without separation by commas.
Keyword arguments may be specified using colons (`:`) instead of equal signs (`=`).

<table>

<tr><th>Craftr DSL</th><th>Python</th></tr>

<tr><td>

```py
print 'Hello, World!' 42 * 1 + 10 file: sys.stdout
```
</td><td>

```py
print('Hello, World!', 42 * 1 + 10, file=sys.stdout)
```
</td></tr>


<tr><td>

```py
task "hello_world" do: {
  print "Hello, World!"
}
```
</td><td>

```py
def _closure_1(self, *arguments, **kwarguments):
    print('Hello, World!')
task('hello_world', do=_closure_1)
```
</td></tr>


<tr><td>

```py
list(map {
  print('Hello,', self)
}, ['John', 'World'])
```

> **Note**: Pitfall, this actually passes three arguments to `list()`.
</td><td>

```py
def _closure_1(self, *arguments, **kwarguments):
    print('Hello,', self)
list(map, _closure_1, ['John', 'World'])
```
</td></tr>

</table>


### Dynamic name resolution <sup>(non-default)</sup>

For some purposes and applications, dynamic name resolution may be desirable, for
example when writing `self` in front of every name to access a property of the closure
target object is too cumbersome. For this, the Craftr DSL transpiler can generate code that
looks up, sets and deletes keys using subscript syntax on a particular variable name.

Using the `craftr.dsl.runtime` package, you can configure the transpiler and runtime
to use dynamic name resolution. Example usage:

```py
from craftr.dsl.transpiler import transpile_to_ast
from craftr.dsl.runtime import Closure

class Project:
  def task(self, name: str, *, do: callable): ...

code = ...
filename = ...

# Long form:
module = transpile_to_ast(code, filename, Closure.get_options())
code = compile(module, filename, 'exec')
scope = {'__closure__': Closure(None, None, Project())}
exec(code, scope)

# Shorthand form:
Closure(None, None, Project()).run_code(code, filename)
```

The `Closure.get_options()` function returns `TranspileOptions` that instruct the transpiler
to convert name lookups into subscripts on the `__closure__` variable, add a
`@__closure__.child` decoration before every closure function definition and to add a
`__closure__,` argument to their arglist. The `Closure` object passed into the `scope`
on execution deals with the rest.

<table>

<tr><th>Craftr DSL</th><th>Python</th></tr>

<tr><td>

```py
task "foobar" do: {
  return n_times
}

task "belzebub" do: {
  def n_times = 1
  return n_times
}

task "cheeky" do: {
  def n_times = 1
  return (() -> n_times )()
}
```
</td><td>

```py
@__closure__.child
def _closure_1(__closure__, self, *arguments, **kwarguments):
    return __closure__['n_times']
__closure__['task']('foobar', do=_closure_1)

@__closure__.child
def _closure_2(__closure__, self, *arguments, **kwarguments):
    n_times = 1
    return n_times
__closure__['task']('belzebub', do=_closure_2)

@__closure__.child
def _closure_3(__closure__, self, *arguments, **kwarguments):
    n_times = 1
    @__closure__.child
    def _closure_3_closure_3(__closure__):
        return n_times
    return _closure_3_closure_3()
__closure__['task']('cheeky', do=_closure_3)
```

</td></tr>

</table>


### Limitations

Craftr DSL is intended to behave as a complete syntactic superset of standard Python. However there are currently
some limitations, namely:

* Literal sets cannot be expressed due to the grammar conflict with parameter-less closures
* Type annotations are not currently supported
* The walrus operator is not currently supported
* Function calls without parenthesis do not support passing `*args` as the first argument as that is
  interpreted as a multiplication expression.

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
