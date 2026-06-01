<h1 align="center">
    <img src="./resources/logo.png" height="300">
    <br />
    Bob the Builder
    <br />
    <img src="https://img.shields.io/badge/license-MIT-blue.svg">
    <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg">
</h1>

<h4 align="center">
    The ergonomic Ninja-based build system.
</h4>

<p align="center">
    🏃 <a href="#getting-started">Getting Started</a>
    &nbsp;&middot&nbsp;
    ⌨️ <a href="#cli">CLI</a>
    &nbsp;&middot&nbsp;
    🎯 <a href="#goals">Goals</a>
    &nbsp;&middot&nbsp;
    🙏 <a href="#acknowledgements">Acknowledgements</a>
</p>

## Getting Started

This is Bob. Bob builds your Bobfiles.

```bash
uvx --from git+https://github.com/noamzaks/bob bob --help
```

Bob doesn't need much boilerplate to build stuff.

```python
from bob.prelude import *

Rule("echo hi > $out").build("demo")

# This will always be run, and when its output changes, the appropriate build file will be changed as well (and all dependant targets will be rebuilt).
GenerateRule("git rev-parse HEAD").build("commit")
```

Bob is fast and doesn't reconfigure Ninja from your Bobfiles unless necessary.

Bob lets you be type-safe with your variables, escape them correctly, and make sure they aren't used uninitialized.

```python
cc = Rule("$ccbin -MMD -MT $out -MF $out.d $cflags -fdiagnostics-color=always -c $in -o $out")
# Set the value of the given rule variables. 
cc["cflags"].provide(["-Wall", "-Wextra"])
# Extend the array value of the given rule variables.
cc["cflags"].extend(["-DDEBUG"])
```

Bob also lets you scope these changes.

```python
with cc["cflags"].extend(["-Wno-unused-variable"]):
    ...
```

Bob has simple build configuration, e.g. `bob build -c DEBUG=y` with:

```python
if config("DEBUG") == "y":
    c.cflags.extend(["-DDEBUG"])
```

Bob lets you utilize the power of Python when configuring, while tracking dependencies for reconfiguring.

```python
from pathlib import Path

src = Path("src")

targets = json.loads(read("targets.json"))
modules = glob("*.c", path=src / "modules")
magic = shell("cat magic")
```

Bob has a plugin for C projects which provides simple abstractions over a toolchain.

```python
import bob.plugins.c as c

c.toolchain(ccbin=["gcc"], arbin=["ar"])

mylib = c.static_library_bundle(
    "mylib", sources=["mylib.c"], public_cflags=[f"-I{srcdir()}"]
)

c.binary("mybin", sources=["my_main.c"], bundles=[mylib])
```

Bob lets you override your rules inside a scope.

```python
my_cc = Rule(
    "$ccbin $cflags -c overridden.c -o $out; echo hi > $out.hi",
    description="CC",
    implicit_outputs=["$out.hi"],
)
with c.cc_provider.provide(my_cc):
    overridden = c.binary("overridden", sources=["dummy.c"])
```

Bob lets you split your build files in the way that works for you.

```python
# `subbob` creates a different scope and uses explicit `export` and `use`.
# The Bobfile inside `src/baselib` must `export("baselib", ...)`.
baselib = subbob("src/baselib").use("baselib", type=c.Bundle)
# The Bobfile inside `src/mylib` can `use("baselib")`.
mylib = subbob("src/mylib", provides:{"baselib": baselib}).use("mylib", type=c.Bundle)

# `include` uses the current scope.
include("targets")
```

Bob has pretty output and can export compile commands.

**Be like Bob.**

## CLI

```bash
# Build the project in the current directory (you should have a Bobfile).
bob build
# Clean the outputs of Bob.
bob clean
# Build with a specific config.
bob build -c DEBUG=n
# Build with a specific config in a separate build directory, so both consecutive builds are blazingly fast.
bob build -c DEBUG=y --builddir build-debug
# More options.
bob build --clean -j 4 --verbose --force-reconfigure
# Create a compile_commands.json.
bob compdb -c DEBUG=n
```

## Goals

Sorted by priority:

- **Writing Bobfiles, writing plugins and rules, and composing Bobfiles** should all be easy and feel Pythonic.
- **Type safety** should allow for a smooth editing experience and easy-to-debug errors.
- **Plugins should be close to the actual commands** rather than lock you in to a specific paradigm.
- **Speed** should be fast.

## Acknowledgements

- [Bake](https://github.com/nmraz/bake/)
- [Kbuild](https://docs.kernel.org/kbuild/)
- [Ninja's configure.py](https://github.com/ninja-build/ninja/blob/master/configure.py)
- Thanks to everyone who helped design Bob, in particular Noam Raz.
