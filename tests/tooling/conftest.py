"""Fixture repositories for the tooling tests.

The tooling is tested at its command line: a test builds a repository tree, runs
the script as a subprocess against it, and asserts what comes back on stdout.
Nothing imports the scripts, so their internals stay free to change without a
test having to move.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"


def _uv_lock(core_version: str) -> str:
    """The few lines of a uv.lock the plan script actually reads."""
    return textwrap.dedent(
        f"""\
        version = 1
        requires-python = ">=3.12"

        [[package]]
        name = "molecule"
        version = "26.8.0"
        source = {{ registry = "https://pypi.org/simple" }}

        [[package]]
        name = "ansible-core"
        version = "{core_version}"
        source = {{ registry = "https://pypi.org/simple" }}
        """
    )


@dataclass
class Repo:
    """A fixture repository tree, plus the runners that act on it."""

    path: Path

    def write(self, relative: str, content: str) -> None:
        target = self.path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def add_role(
        self,
        name: str,
        platforms: dict[str, list[str]] | None = None,
    ) -> None:
        """Add a role. ``platforms`` maps a galaxy_info name to its versions."""
        platforms = platforms if platforms is not None else {"EL": ["8", "9", "10"]}
        declared = [
            {"name": key, "versions": versions} for key, versions in platforms.items()
        ]
        meta = {
            "galaxy_info": {
                "author": "Ohio University IT",
                "description": f"{name} role",
                "license": "GPL-3.0-or-later",
                "min_ansible_version": "2.16",
                "platforms": declared,
            },
            "dependencies": [],
        }
        self.write(f"roles/{name}/meta/main.yml", json.dumps(meta))
        self.write(f"roles/{name}/tasks/main.yml", "---\n[]\n")

    def plan(
        self,
        changed: list[str] | None = None,
        event: str = "pull_request",
        no_cache: bool = False,
    ) -> dict:
        """Run the plan script and return its parsed outputs."""
        argv = [
            sys.executable,
            str(TOOLS / "molecule_plan.py"),
            "--repo-root",
            str(self.path),
            "--event",
            event,
            "--changed-files-from",
            "-",
        ]
        if no_cache:
            argv.append("--no-cache")

        result = subprocess.run(
            argv,
            input="\n".join(changed or []),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        raw = json.loads(result.stdout)
        return {
            "molecule": json.loads(raw["molecule_matrix"])["include"],
            "sanity": json.loads(raw["sanity_matrix"])["include"],
            "roles": json.loads(raw["roles"]),
            "dependency_key": raw["dependency_key"],
            "has_molecule_jobs": raw["has_molecule_jobs"],
        }

    def plan_raw(self, changed: list[str], event: str = "pull_request"):
        """Run the plan script without asserting success."""
        return subprocess.run(
            [
                sys.executable,
                str(TOOLS / "molecule_plan.py"),
                "--repo-root",
                str(self.path),
                "--event",
                event,
                "--changed-files-from",
                "-",
            ],
            input="\n".join(changed),
            capture_output=True,
            text=True,
            check=False,
        )

    def check_defaults(self, *roles: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(TOOLS / "defaults_vs_spec.py"),
                "--repo-root",
                str(self.path),
                *roles,
            ],
            capture_output=True,
            text=True,
            check=False,
        )


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    """A repository with the two Core Lanes locked and one role declared."""
    fixture = Repo(tmp_path)
    fixture.write(
        "galaxy.yml",
        textwrap.dedent(
            """\
            ---
            namespace: ohioit
            name: roles
            version: 0.0.0
            dependencies:
              fedora.linux_system_roles: "2.4.2"
              ansible.posix: ">=2.1.0,<2.2.0"
            """
        ),
    )
    fixture.write("extensions/molecule/requirements.yml", "---\ncollections:\n  - containers.podman\n")
    fixture.write("uv.lock", _uv_lock("2.21.4"))
    fixture.write("lanes/core-2.16/uv.lock", _uv_lock("2.16.19"))
    fixture.add_role("firewall")
    return fixture
