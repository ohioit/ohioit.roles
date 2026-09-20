"""Check that a role's defaults and its argument spec declare the same variables.

``meta/argument_specs.yml`` is the source of truth for a role's interface: it is
what aar-doc turns into the README options table and what ansible-lint's
``role-argument-spec`` rule requires. ``defaults/main.yml`` is what actually
takes effect. Nothing keeps the two in step, and the failure is quiet in both
directions -- a variable documented but never defaulted reads as supported and
isn't, and a variable defaulted but never documented is invisible to users.

This reports and fails. It never edits either file: which of the two is wrong is
a judgement the author has to make.

A spec option marked ``required: true`` is allowed to have no default, since
requiring a value and defaulting it are contradictory.

Run it over every role::

    uv run tools/defaults_vs_spec.py

or over named ones::

    uv run tools/defaults_vs_spec.py firewall
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROLES_DIR = "roles"


def role_names(repo_root: Path, requested: list[str]) -> list[str]:
    if requested:
        return requested
    roles_path = repo_root / ROLES_DIR
    if not roles_path.is_dir():
        return []
    return sorted(p.name for p in roles_path.iterdir() if (p / "tasks").is_dir())


def defaults_variables(role_path: Path) -> set[str]:
    defaults_file = role_path / "defaults" / "main.yml"
    if not defaults_file.is_file():
        return set()
    loaded = yaml.safe_load(defaults_file.read_text()) or {}
    return set(loaded)


def spec_variables(role_path: Path) -> tuple[set[str], set[str]]:
    """Return (all options, options that are required).

    Options are collected across every entry point, since a variable documented
    on any entry point is part of the role's interface.
    """
    spec_file = role_path / "meta" / "argument_specs.yml"
    if not spec_file.is_file():
        return set(), set()
    loaded = yaml.safe_load(spec_file.read_text()) or {}
    entry_points = loaded.get("argument_specs") or {}

    options: set[str] = set()
    required: set[str] = set()
    for spec in entry_points.values():
        for name, definition in (spec.get("options") or {}).items():
            options.add(name)
            if isinstance(definition, dict) and definition.get("required"):
                required.add(name)
    return options, required


def check_role(repo_root: Path, role: str) -> list[str]:
    role_path = repo_root / ROLES_DIR / role
    problems: list[str] = []

    spec_file = role_path / "meta" / "argument_specs.yml"
    if not spec_file.is_file():
        return [
            f"{role}: no meta/argument_specs.yml. Every role ships one -- it is "
            f"what generates the README options table."
        ]

    defaults = defaults_variables(role_path)
    options, required = spec_variables(role_path)

    for name in sorted(defaults - options):
        problems.append(
            f"{role}: `{name}` is in defaults/main.yml but not in "
            f"meta/argument_specs.yml, so it is invisible in the README."
        )
    for name in sorted(options - defaults - required):
        problems.append(
            f"{role}: `{name}` is in meta/argument_specs.yml but has no entry in "
            f"defaults/main.yml. Add a default, or mark the option required."
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roles", nargs="*", help="Roles to check. Default: all of them.")
    parser.add_argument("--repo-root", default=".", type=Path)
    args = parser.parse_args(argv)

    problems: list[str] = []
    for role in role_names(args.repo_root, args.roles):
        problems.extend(check_role(args.repo_root, role))

    if problems:
        print("defaults/main.yml and meta/argument_specs.yml disagree:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(file=sys.stderr)
        return 1

    print("defaults and argument specs agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
