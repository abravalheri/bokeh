#-----------------------------------------------------------------------------
# Copyright (c) 2012 - 2022, Anaconda, Inc., and Bokeh Contributors.
# All rights reserved.
#
# The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Standard library imports
import os, re, subprocess, sys, time
from itertools import product
from pathlib import Path
from shutil import copy, copytree, rmtree
from textwrap import indent
from typing import Iterator, NoReturn

# External imports
from setuptools import Command, setup
from setuptools.command.sdist import sdist
from setuptools.command.build import build

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

try:
    import colorama
    if sys.platform == "win32": colorama.init()
    def bright(text: str) -> str: return f"{colorama.Style.BRIGHT}{text}{colorama.Style.RESET_ALL}"
    def dim(text: str) -> str: return f"{colorama.Style.DIM}{text}{colorama.Style.RESET_ALL}"
    def red(text: str) -> str: return f"{colorama.Fore.RED}{text}{colorama.Style.RESET_ALL}"
    def green(text: str) -> str: return f"{colorama.Fore.GREEN}{text}{colorama.Style.RESET_ALL}"
    def yellow(text: str) -> str: return f"{colorama.Fore.YELLOW}{text}{colorama.Style.RESET_ALL}"
except ModuleNotFoundError:
    def _plain(text: str) -> str: return text
    bright = dim = red = green = yellow = _plain

ROOT = Path(__file__).resolve().parent
BUILD_JS = ROOT / 'bokehjs' / 'build' / 'js'
BUILD_TSLIB = ROOT / 'bokehjs' / 'node_modules' / 'typescript' / 'lib'
PKG_STATIC = ROOT / 'bokeh' / 'server' / 'static'
PKG_JS = PKG_STATIC / 'js'
PKG_TSLIB = PKG_STATIC / 'lib'
COMPONENTS = ("bokeh", "bokeh-widgets", "bokeh-tables", "bokeh-api", "bokeh-gl", "bokeh-mathjax")
JS_FILES = [f"{c}{m}.js" for c, m in product(COMPONENTS, ("", ".min"))]

def build_js() -> None:
    print("\nBuilding BokehJS... ", end="")
    try:
        t0 = time.time()
        proc = subprocess.run(["node", "make", "build"], capture_output=True, cwd="bokehjs")
        t1 = time.time()
    except OSError as e:
        die(BUILD_EXEC_FAIL_MSG.format(exc=e))

    if proc.returncode != 0:
        out = indent(proc.stdout.decode('ascii', errors='ignore'), '    ')
        err = indent(proc.stderr.decode('ascii', errors='ignore'), '    ')
        die(BUILD_FAIL_MSG.format(stdout=red(out), stderr=red(err)))

    out = proc.stdout.decode('ascii', errors='ignore')
    pat = re.compile(r"(\[.*\]) (.*)", re.DOTALL)
    msg = []
    for line in out.strip().split("\n"):
        if m := pat.match(line):
            stamp, txt = m.groups()
            msg.append(f"   {dim(green(stamp))} {dim(txt)}")
    print(BUILD_SUCCESS_MSG.format(msg="\n".join(msg)))
    print(f"\n Build time: {bright(yellow(f'{t1-t0:0.1f} seconds'))}\n")

    print("Build artifact sizes:")
    try:
        for fn in JS_FILES:
            size = (BUILD_JS / fn).stat().st_size / 2**10
            print(f"  - {fn:<20} : {size:6.1f} KB")
    except FileNotFoundError as e:
        die(BUILD_SIZE_FAIL_MSG.format(exc=e))

def install_js() -> None:
    print("\nInstalling BokehJS... ", end="")

    missing = [fn for fn in JS_FILES if not (BUILD_JS / fn).exists()]
    if missing:
        die(BOKEHJS_INSTALL_FAIL.format(missing=", ".join(missing)))

    if PKG_JS.exists():
        rmtree(PKG_JS)
    copytree(BUILD_JS, PKG_JS)

    if PKG_TSLIB.exists():
        rmtree(PKG_TSLIB)
    if BUILD_TSLIB.exists():
        PKG_TSLIB.mkdir()
        for lib_file in BUILD_TSLIB.glob("lib.*.d.ts"):
            copy(lib_file, PKG_TSLIB)

    print(SUCCESS)

def build_or_install_bokehjs() -> None:
    action = os.environ.get("BOKEHJS_ACTION", "build")
    if (ROOT / 'PKG-INFO').exists():
        kind, loc = "PACKAGED", "bokeh.server.static"
    elif action == "install":
        install_js()
        kind, loc = "PREVIOUSLY BUILT", "bokehjs/build"
    elif action == "build":
        build_js()
        install_js()
        kind, loc = "NEWLY BUILT", "bokehjs/build"
    else:
        raise ValueError(f"Unrecognized action {action!r}")
    print(f"Used {bright(yellow(kind))} BokehJS from {loc}\n")

def die(x: str) -> NoReturn:
    print(f"{x}\n")
    sys.exit(1)

SUCCESS = f"{bright(green('Success!'))}\n"
FAILED = f"{bright(red('Failed.'))}\n"
BUILD_SUCCESS_MSG =f"{SUCCESS}\nBuild output:\n\n{{msg}}"
BUILD_SIZE_FAIL_MSG = f"{FAILED}\nERROR: could not determine sizes:\n\n     {{exc}}"
BOKEHJS_INSTALL_FAIL = f"{FAILED}\nERROR: Cannot install BokehJS: files missing in bokehjs/build:\n\n    {{missing}}"
BUILD_EXEC_FAIL_MSG = f"{FAILED}\nERROR: 'node make build' failed to execute:\n\n    {{exc}}"
BUILD_FAIL_MSG = f"""{FAILED}\nERROR: 'node make build' returned the following

---- on stdout:
{{stdout}}

---- on stderr:
{{stderr}}
"""

# -----------------------------------------------------------------------------
# Setuptools
# -----------------------------------------------------------------------------

# JS files should be available from the sdist, to avoid requiring users
# to setup a JS development environment when building from source.
# This would normally mean that BuildJS is eligible as an sdist sub-command.
# However `sdist` does not run during editable installs, so we also need BuildJS
# to be a sub-command of build.

class Sdist(sdist):
    sub_commands = [("build_js", None), *sdist.sub_commands]

class Build(build):
    sub_commands = [("build_js_editable_mode", None), *build.sub_commands]

class BuildJS(Command):
    def initialize_options(self) -> None: pass
    def finalize_options(self) -> None: pass

    def run(self) -> None:
        build_or_install_bokehjs()
        self.add_missing_packages()

    def add_missing_packages(self) -> None:
        """Add packages that may not exist on disk when packages.find configuration is expanded."""
        extra = (
            ".".join([*Path(parent).relative_to(ROOT).parts, d])
            for parent, dirs, _ in os.walk(PKG_STATIC)
            for d in dirs
        )
        already_included = set(self.distribution.packages)
        missing = (p for p in extra if p not in already_included)
        self.distribution.packages.extend(missing)

class BuildJSEditableMode(BuildJS):
    def initialize_options(self) -> None:
        self.editable_mode = False
    def run(self) -> None:
        if self.editable_mode:  # set by setuptools
            super().run()

setup(
    cmdclass={
        "sdist": Sdist,
        "build": Build,
        "build_js": BuildJS,
        "build_js_editable_mode": BuildJSEditableMode,
    }
)
