# -----------------------------------------------------------------------------
# Copyright (c) 2012 - 2022, Anaconda, Inc., and Bokeh Contributors.
# All rights reserved.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# -----------------------------------------------------------------------------
"""

"""
from __future__ import annotations

# Standard library imports
import json
from typing import Any, Callable

# Bokeh imports
from .action import FAILED, PASSED, ActionReturn
from .config import Config
from .system import System
from .util import skip_for_prerelease

__all__ = (
    "build_bokehjs",
    "build_conda_packages",
    "build_docs",
    "build_pip_packages",
    "dev_install",
    "install_bokehjs",
    "npm_install",
    "pack_deployment_tarball",
    "update_bokehjs_versions",
    "update_changelog",
    "update_hash_manifest",
)


def build_bokehjs(config: Config, system: System) -> ActionReturn:
    try:
        system.cd("bokehjs")
        system.run("node make build")
        system.cd("..")
        return PASSED("BokehJS build succeeded")
    except RuntimeError as e:
        return FAILED("BokehJS build did NOT succeed", details=e.args)


def build_npm_packages(config: Config, system: System) -> ActionReturn:
    try:
        system.cd("bokehjs")
        system.run("npm pack")
        system.cd("..")
        return PASSED("npm pack succeeded")
    except RuntimeError as e:
        return FAILED("npm pack did NOT succeed", details=e.args)


def build_conda_packages(config: Config, system: System) -> ActionReturn:
    try:
        system.run("conda build conda.recipe --no-test --output-folder .", VERSION=config.version)
        return PASSED("conda package build succeeded")
    except RuntimeError as e:
        return FAILED("conda package build did NOT succeed", details=e.args)


def build_docs(config: Config, system: System) -> ActionReturn:
    try:
        system.cd("sphinx")
        system.run("make clean all", BOKEH_DOCS_CDN=config.version, BOKEH_DOCS_VERSION=config.version)
        system.cd("..")
        return PASSED("Docs build succeeded")
    except RuntimeError as e:
        return FAILED("Docs build did NOT succeed", details=e.args)


def build_pip_packages(config: Config, system: System) -> ActionReturn:
    try:
        system.run("python -m build .", BOKEHJS_ACTION="install")
        return PASSED("pip packages build succeeded")
    except RuntimeError as e:
        return FAILED("pip packages build did NOT succeed", details=e.args)


def dev_install(config: Config, system: System) -> ActionReturn:
    try:
        system.run("pip install -e .", BOKEHJS_ACTION="install")
        return PASSED("Bokeh dev install succeeded")
    except RuntimeError as e:
        return FAILED("Bokeh dev install did NOT succeed", details=e.args)


def install_bokehjs(config: Config, system: System) -> ActionReturn:
    try:
        system.run("pip install .", BOKEHJS_ACTION="install")
        return PASSED("BokehJS install succeeded")
    except RuntimeError as e:
        return FAILED("BokehJS install did NOT succeed", details=e.args)


def npm_install(config: Config, system: System) -> ActionReturn:
    try:
        system.cd("bokehjs")
        system.run("npm ci")
        system.cd("..")
        return PASSED("npm ci succeeded")
    except RuntimeError as e:
        return FAILED("npm ci did NOT succeed", details=e.args)


def pack_deployment_tarball(config: Config, system: System) -> ActionReturn:
    try:
        dirname = f"deployment-{config.version}"
        filename = f"{dirname}.tgz"
        system.run(f"mkdir {dirname}")
        system.run(f"cp bokehjs/bokeh-bokehjs-{config.js_version}.tgz {dirname}")
        system.run(f"cp noarch/bokeh-{config.version}-py_0.tar.bz2 {dirname}")
        system.run(f"cp dist/bokeh-{config.pep440_version}.tar.gz {dirname}")
        system.run(f"cp dist/bokeh-{config.pep440_version}-py3-none-any.whl {dirname}")
        system.run(f"mkdir {dirname}/bokehjs")
        system.run(f"cp -r bokehjs/build {dirname}/bokehjs")
        system.run(f"mkdir -p {dirname}/sphinx/build")
        system.run(f"cp -r sphinx/build/html {dirname}/sphinx/build")
        system.run(f"cp -r sphinx/switcher.json {dirname}/sphinx")
        system.run(f"tar cvf {filename} {dirname}")
        return PASSED(f"Packed deployment tarball {filename!r}")
    except RuntimeError as e:
        return FAILED("Could NOT pack deployment tarball", details=e.args)


def update_bokehjs_versions(config: Config, system: System) -> ActionReturn:
    def update_package_json(content: dict[str, Any]) -> None:
        content["version"] = config.js_version

    def update_package_lock_json(content: dict[str, Any]) -> None:
        assert content["lockfileVersion"] == 2, "Expected lock file v2"
        content["version"] = config.js_version
        for pkg in content["packages"].values():
            if pkg.get("name", "").startswith("@bokeh/"):
                pkg["version"] = config.js_version

    files: dict[str, Callable[[dict[str, Any]], None]] = {
        "package.json": update_package_json,
        "make/package.json": update_package_json,
        "src/compiler/package.json": update_package_json,
        "src/lib/package.json": update_package_json,
        "src/server/package.json": update_package_json,
        "test/package.json": update_package_json,
        "package-lock.json": update_package_lock_json,
    }

    system.pushd("bokehjs")

    for filename, action in files.items():
        content = json.load(open(filename))
        try:
            action(content)

            with open(filename, "w") as f:
                json.dump(content, f, indent=2)
                f.write("\n")
            config.add_modified(f"bokehjs/{filename}")
        except Exception as e:
            return FAILED(f"Unable to write new version to file {filename!r}", details=e.args)

    system.popd()

    return PASSED(f"Updated version to {config.js_version!r} in files: {list(files.keys())!r}")


@skip_for_prerelease
def update_changelog(config: Config, system: System) -> ActionReturn:
    try:
        system.pushd("scripts")
        system.run(f"python milestone.py -a {config.milestone_version}")
        system.popd()
        config.add_modified("CHANGELOG")
        return PASSED("Updated CHANGELOG with new closed issues")
    except RuntimeError as e:
        return FAILED("CHANGELOG update failed", details=e.args)


@skip_for_prerelease
def update_hash_manifest(config: Config, system: System) -> ActionReturn:
    try:
        system.cd("scripts")
        system.run(f"python sri.py {config.version}")
        system.cd("..")
        config.add_modified("bokeh/_sri.json")
        return PASSED("Updated SRI hash manifest")
    except RuntimeError as e:
        return FAILED("SRI hash manifest update failed", details=e.args)
