"""Work out what CI should run, and emit the matrices for it.

This is the only file in the repository that holds the Core Lane table, and the
only one that parses ``galaxy.yml``'s dependencies. Workflows read versions from
here rather than carrying their own copies, so a Renovate bump of a lock file
moves that lane everywhere at once -- Molecule jobs and sanity jobs together --
with no workflow edit.

It emits three things:

* the Molecule matrix: one entry per role x Target Platform x Core Lane
* the sanity matrix: one ``stable-X.Y`` per Core Lane, read from its ``uv.lock``
* the collection dependency cache key

Run it directly to see the plan for a working tree::

    uv run tools/molecule_plan.py --event pull_request --changed-files-from -

See ``tests/tooling/test_molecule_plan.py`` for the behaviour this guarantees.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# --------------------------------------------------------------------------
# The Core Lane table.
#
# Adding or retiring a Core Lane is an edit here and nowhere else. When RHEL 8
# retires (2029-05-31), delete the "2.16" entry and the lanes/core-2.16/
# directory; nothing in .github/workflows/ mentions either.
#
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Lane:
    """One supported ansible-core minor version and the project that pins it."""

    #: Path to the lane's uv project, relative to the repository root.
    uv_project: str
    #: Controller Python. 2.16 stops at 3.12; 2.22 will start at 3.13, so no
    #: single interpreter spans both lanes and each carries its own.
    python: str
    #: uv's cache key input for this lane. Deliberately narrower than
    #: setup-uv's repo-wide default, which would give both lanes one shared key
    #: and let a root lock bump silently cold-start the 2.16 lane.
    cache_dependency_glob: str


LANES: dict[str, Lane] = {
    "2.16": Lane(
        uv_project="lanes/core-2.16",
        python="3.12",
        cache_dependency_glob="lanes/core-2.16/uv.lock",
    ),
    "current": Lane(
        uv_project=".",
        python="3.14",
        cache_dependency_glob="uv.lock\npyproject.toml",
    ),
}

# --------------------------------------------------------------------------
# The Target Platform table.
#
# Adding Windows later is a row here plus a branch in
# extensions/molecule/create.yml. The shape of molecule.yml does not change.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Platform:
    """A Target Platform: an OS major version a role is tested against."""

    #: GitHub runner label.
    runs_on: str
    #: How the host is stood up. Only "container" exists today; a Windows row
    #: would add its own kind and create.yml would branch on it.
    kind: str
    #: Which Core Lanes test this platform. EL8 is 2.16-only because no later
    #: ansible-core manages a stock RHEL 8 host. EL9 and EL10 run both, because
    #: a controller that manages RHEL 8 usually manages the rest of the fleet.
    lanes: tuple[str, ...]


PLATFORMS: dict[str, Platform] = {
    "el8": Platform(runs_on="ubuntu-latest", kind="container", lanes=("2.16",)),
    "el9": Platform(runs_on="ubuntu-latest", kind="container", lanes=("2.16", "current")),
    "el10": Platform(runs_on="ubuntu-latest", kind="container", lanes=("2.16", "current")),
}

#: galaxy_info.platforms names map to host names by lowercasing and appending
#: the version: EL + "8" -> el8. The inventory in extensions/molecule/ uses the
#: same names.
PLATFORM_NAME_ALIASES = {"el": "el"}

# --------------------------------------------------------------------------
# Change detection.
# --------------------------------------------------------------------------

#: A change to any of these reaches every role, so every role is tested.
#:
#: .release-please-manifest.json and galaxy.yml are both rewritten by the
#: Release PR, which is exactly why that pull request fans out to everything --
#: without depending on its branch name, which release-please is free to change.
FANOUT_PATTERNS: tuple[str, ...] = (
    "galaxy.yml",
    ".release-please-manifest.json",
    "release-please-config.json",
    "pyproject.toml",
    "uv.lock",
    ".mise.toml",
    "lanes/**",
    "tools/**",
    ".github/workflows/molecule.yml",
)

#: Events that test everything regardless of the diff.
FANOUT_EVENTS = frozenset({"push", "schedule", "workflow_dispatch"})

ROLES_DIR = "roles"
SCENARIOS_DIR = "extensions/molecule"
TEST_REQUIREMENTS = "extensions/molecule/requirements.yml"


def _matches(path: str, pattern: str) -> bool:
    """Match a repo-relative path against a glob, treating ``**`` as recursive."""
    if pattern.endswith("/**"):
        return path == pattern[:-3] or path.startswith(pattern[:-2])
    return fnmatch.fnmatch(path, pattern)


def discover_roles(repo_root: Path) -> list[str]:
    """Every role in the collection, in a stable order."""
    roles_path = repo_root / ROLES_DIR
    if not roles_path.is_dir():
        return []
    return sorted(p.name for p in roles_path.iterdir() if (p / "tasks").is_dir())


def platforms_for_role(repo_root: Path, role: str) -> list[str]:
    """Read a role's Target Platforms from its own ``meta/main.yml``.

    The declaration is the contract: whatever a role says it supports is what
    CI tests it against. An unknown platform is an error rather than a silent
    skip, because silently testing less than a role claims is the failure this
    whole arrangement exists to prevent.
    """
    meta_path = repo_root / ROLES_DIR / role / "meta" / "main.yml"
    if not meta_path.is_file():
        return []
    meta = yaml.safe_load(meta_path.read_text()) or {}
    declared = (meta.get("galaxy_info") or {}).get("platforms") or []

    hosts: list[str] = []
    for entry in declared:
        name = str(entry.get("name", "")).strip().lower()
        name = PLATFORM_NAME_ALIASES.get(name, name)
        for version in entry.get("versions") or []:
            host = f"{name}{version}"
            if host not in PLATFORMS:
                raise SystemExit(
                    f"{meta_path}: platform {entry.get('name')} {version} "
                    f"(host {host!r}) has no row in this script's PLATFORMS "
                    f"table. Add one, or fix the role's meta/main.yml."
                )
            hosts.append(host)
    return hosts


def roles_to_test(
    repo_root: Path,
    changed: list[str],
    event: str,
) -> list[str]:
    """Which roles this run should test."""
    all_roles = discover_roles(repo_root)
    if event in FANOUT_EVENTS:
        return all_roles

    for path in changed:
        if any(_matches(path, pattern) for pattern in FANOUT_PATTERNS):
            return all_roles
        # Shared scenario plumbing -- config.yml, create.yml, destroy.yml,
        # inventory.yml, requirements.yml -- is anything directly under
        # extensions/molecule/ rather than inside a role's scenario directory.
        if path.startswith(f"{SCENARIOS_DIR}/"):
            remainder = path[len(SCENARIOS_DIR) + 1 :]
            if "/" not in remainder:
                return all_roles

    selected: set[str] = set()
    for role in all_roles:
        prefixes = (f"{ROLES_DIR}/{role}/", f"{SCENARIOS_DIR}/{role}/")
        if any(path.startswith(prefix) for prefix in prefixes for path in changed):
            selected.add(role)
    return [role for role in all_roles if role in selected]


def locked_core_version(repo_root: Path, lane: Lane) -> str:
    """The ansible-core minor a lane's ``uv.lock`` currently pins.

    Read rather than written down, so a Renovate bump of the lock file moves the
    lane's Molecule jobs and its sanity job together and no workflow has to be
    edited.
    """
    lock_path = repo_root / lane.uv_project / "uv.lock"
    data = tomllib.loads(lock_path.read_text())
    for package in data.get("package", []):
        if package.get("name") == "ansible-core":
            version = package["version"]
            match = re.match(r"^(\d+\.\d+)", version)
            if not match:
                raise SystemExit(f"{lock_path}: unreadable ansible-core version {version!r}")
            return match.group(1)
    raise SystemExit(f"{lock_path}: no ansible-core entry found")


def dependency_cache_key(repo_root: Path) -> str:
    """Key for the ~/.ansible/collections cache.

    Derived from the *extracted* ``dependencies`` mapping rather than a hash of
    galaxy.yml, because release-please rewrites that file's version line on
    every Release PR -- the single most expensive run in the repo, since the
    same rewrite is what makes it fan out to every role. Hashing the file would
    guarantee that run starts cold.

    The workflow uses this with an exact match and no restore-keys. A prefix
    fallback would restore the previous tree and install on top of it, which is
    exactly how a Shipped Dependency removed from galaxy.yml survives in CI
    forever while breaking for real users.
    """
    galaxy = yaml.safe_load((repo_root / "galaxy.yml").read_text()) or {}
    shipped = galaxy.get("dependencies") or {}

    test_only_path = repo_root / TEST_REQUIREMENTS
    test_only = test_only_path.read_text() if test_only_path.is_file() else ""

    payload = json.dumps(
        {"shipped": shipped, "test_only": test_only},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


@dataclass
class Plan:
    molecule_include: list[dict] = field(default_factory=list)
    sanity_include: list[dict] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    dependency_key: str = ""

    @property
    def has_molecule_jobs(self) -> bool:
        return bool(self.molecule_include)


def build_plan(
    repo_root: Path,
    changed: list[str],
    event: str,
    no_cache: bool,
) -> Plan:
    plan = Plan(dependency_key=dependency_cache_key(repo_root))
    plan.roles = roles_to_test(repo_root, changed, event)

    for lane_name, lane in LANES.items():
        core = locked_core_version(repo_root, lane)
        plan.sanity_include.append(
            {
                "lane": lane_name,
                "ansible_core": core,
                "ansible": f"stable-{core}",
                "python": lane.python,
                "uv_project": lane.uv_project,
                "cache_dependency_glob": lane.cache_dependency_glob,
                "runs_on": "ubuntu-latest",
            }
        )

    for role in plan.roles:
        for host in platforms_for_role(repo_root, role):
            platform = PLATFORMS[host]
            for lane_name in platform.lanes:
                lane = LANES[lane_name]
                core = locked_core_version(repo_root, lane)
                plan.molecule_include.append(
                    {
                        # Carried into the job name, so a red X in the checks
                        # list says which role, which platform and which lane
                        # without opening the logs.
                        "name": f"{role} / {host} / core {core}",
                        "role": role,
                        "platform": host,
                        "kind": platform.kind,
                        "lane": lane_name,
                        "ansible_core": core,
                        "python": lane.python,
                        "uv_project": lane.uv_project,
                        "cache_dependency_glob": lane.cache_dependency_glob,
                        "runs_on": platform.runs_on,
                        # The weekly run goes cold so that a real Galaxy install
                        # is proven once a week. See ticket 12.
                        "no_cache": no_cache,
                    }
                )
    return plan


def read_changed(source: str | None) -> list[str]:
    if source is None:
        return []
    text = sys.stdin.read() if source == "-" else Path(source).read_text()
    return [line.strip() for line in text.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", type=Path)
    parser.add_argument(
        "--event",
        default="pull_request",
        help="GitHub event name. push, schedule and workflow_dispatch test everything.",
    )
    parser.add_argument(
        "--changed-files-from",
        help="File holding the changed paths, one per line, or - for stdin.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Mark the emitted jobs to skip the collection cache (the weekly run).",
    )
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="Also append the outputs to $GITHUB_OUTPUT.",
    )
    args = parser.parse_args(argv)

    plan = build_plan(
        repo_root=args.repo_root,
        changed=read_changed(args.changed_files_from),
        event=args.event,
        no_cache=args.no_cache,
    )

    outputs = {
        "molecule_matrix": json.dumps({"include": plan.molecule_include}),
        "sanity_matrix": json.dumps({"include": plan.sanity_include}),
        "roles": json.dumps(plan.roles),
        "dependency_key": plan.dependency_key,
        # Lets the test job be skipped outright rather than started with an
        # empty matrix. The Result Job treats that skip as success on purpose.
        "has_molecule_jobs": str(plan.has_molecule_jobs).lower(),
    }

    print(json.dumps(outputs, indent=2))

    if args.github_output:
        github_output = os.environ.get("GITHUB_OUTPUT")
        if not github_output:
            raise SystemExit("--github-output given but $GITHUB_OUTPUT is not set")
        with open(github_output, "a", encoding="utf-8") as handle:
            for key, value in outputs.items():
                handle.write(f"{key}={value}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
