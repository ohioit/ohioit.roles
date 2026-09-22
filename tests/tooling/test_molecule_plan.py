"""What the plan script promises the workflows.

The dangerous failure here is not a crash, it is a wrong matrix that still looks
green: a plan bug that emits no jobs reads exactly like a pull request that
needed no jobs. So the empty-matrix case is pinned as deliberately as the
fan-out ones.
"""

from __future__ import annotations


def jobs(plan) -> set[tuple[str, str, str]]:
    return {(job["role"], job["platform"], job["lane"]) for job in plan["molecule"]}


# --------------------------------------------------------------------------
# Which roles run
# --------------------------------------------------------------------------


def test_a_role_change_runs_that_role_on_every_platform_and_lane(repo):
    plan = repo.plan(changed=["roles/firewall/tasks/main.yml"])

    assert jobs(plan) == {
        ("firewall", "el8", "2.16"),
        ("firewall", "el9", "2.16"),
        ("firewall", "el9", "current"),
        ("firewall", "el10", "2.16"),
        ("firewall", "el10", "current"),
    }


def test_a_scenario_change_runs_its_own_role(repo):
    repo.add_role("motd")
    plan = repo.plan(changed=["extensions/molecule/firewall/converge.yml"])

    assert plan["roles"] == ["firewall"]


def test_only_the_changed_role_runs(repo):
    repo.add_role("motd")
    plan = repo.plan(changed=["roles/motd/defaults/main.yml"])

    assert plan["roles"] == ["motd"]


def test_documentation_only_change_produces_an_empty_matrix(repo):
    plan = repo.plan(changed=["README.md", "docs/github-repo-settings.md"])

    assert plan["molecule"] == []
    assert plan["roles"] == []
    # The workflow skips the test job outright on this, and the Result Job
    # treats that skip as success. This is the false-green case: if the plan
    # script ever emitted this for a real role change, CI would go green having
    # tested nothing.
    assert plan["has_molecule_jobs"] == "false"


def test_a_changed_role_is_never_reported_as_no_jobs(repo):
    plan = repo.plan(changed=["roles/firewall/tasks/build.yml"])

    assert plan["has_molecule_jobs"] == "true"


# --------------------------------------------------------------------------
# Fan-out
# --------------------------------------------------------------------------


def test_collection_wide_changes_run_every_role(repo):
    repo.add_role("motd")

    for path in (
        "galaxy.yml",
        "CHANGELOG.md",
        "changelogs/fragments/x.yml",
        "lanes/core-2.16/uv.lock",
        "uv.lock",
        "pyproject.toml",
        ".mise.toml",
        "tools/molecule_plan.py",
        ".github/workflows/molecule.yml",
        "extensions/molecule/create.yml",
        "extensions/molecule/inventory.yml",
    ):
        plan = repo.plan(changed=[path])
        assert plan["roles"] == ["firewall", "motd"], f"{path} should fan out"


def test_the_release_pull_request_fans_out_without_knowing_its_branch_name(repo):
    repo.add_role("motd")
    # `mise run release` rewrites exactly these, and nothing about the branch
    # name is relied on.
    plan = repo.plan(changed=["galaxy.yml", "CHANGELOG.md"])

    assert plan["roles"] == ["firewall", "motd"]


def test_push_and_schedule_run_everything_regardless_of_the_diff(repo):
    repo.add_role("motd")

    for event in ("push", "schedule", "workflow_dispatch"):
        plan = repo.plan(changed=["README.md"], event=event)
        assert plan["roles"] == ["firewall", "motd"], event


# --------------------------------------------------------------------------
# Target Platforms come from the role
# --------------------------------------------------------------------------


def test_a_role_declaring_fewer_platforms_gets_fewer_jobs(repo):
    repo.add_role("el9only", platforms={"EL": ["9"]})
    plan = repo.plan(changed=["roles/el9only/tasks/main.yml"])

    assert jobs(plan) == {
        ("el9only", "el9", "2.16"),
        ("el9only", "el9", "current"),
    }


def test_el8_runs_only_the_2_16_lane(repo):
    plan = repo.plan(changed=["roles/firewall/tasks/main.yml"])
    el8_lanes = {job["lane"] for job in plan["molecule"] if job["platform"] == "el8"}

    # No later ansible-core manages a stock RHEL 8 host, so an el8/current job
    # would be testing a combination nobody can run.
    assert el8_lanes == {"2.16"}


def test_an_unknown_platform_is_an_error_not_a_silent_skip(repo):
    repo.add_role("solaris", platforms={"Solaris": ["11"]})
    result = repo.plan_raw(["roles/solaris/tasks/main.yml"])

    assert result.returncode != 0
    assert "PLATFORMS" in result.stderr


# --------------------------------------------------------------------------
# Versions are read, never written down
# --------------------------------------------------------------------------


def test_the_sanity_matrix_is_read_from_each_lane_lock_file(repo):
    plan = repo.plan(changed=[])

    assert {entry["ansible"] for entry in plan["sanity"]} == {"stable-2.16", "stable-2.21"}


def test_moving_a_lane_lock_moves_the_sanity_matrix(repo):
    repo.write("uv.lock", repo.path.joinpath("uv.lock").read_text().replace("2.21.4", "2.22.0"))
    plan = repo.plan(changed=[])

    assert {entry["ansible"] for entry in plan["sanity"]} == {"stable-2.16", "stable-2.22"}


def test_each_lane_carries_its_own_python_and_project(repo):
    plan = repo.plan(changed=["roles/firewall/tasks/main.yml"])
    by_lane = {job["lane"]: job for job in plan["molecule"]}

    assert by_lane["2.16"]["python"] == "3.12"
    assert by_lane["2.16"]["uv_project"] == "lanes/core-2.16"
    assert by_lane["current"]["python"] == "3.14"
    assert by_lane["current"]["uv_project"] == "."


def test_each_lane_caches_on_its_own_lock_file(repo):
    plan = repo.plan(changed=["roles/firewall/tasks/main.yml"])
    globs = {job["lane"]: job["cache_dependency_glob"] for job in plan["molecule"]}

    # setup-uv's default glob is repo-wide, which would give both lanes one key
    # and let a root lock bump silently cold-start the 2.16 lane.
    assert globs["2.16"] == "lanes/core-2.16/uv.lock"
    assert "lanes/" not in globs["current"]


# --------------------------------------------------------------------------
# The collection cache key
# --------------------------------------------------------------------------


def test_the_cache_key_ignores_the_version_line(repo):
    before = repo.plan(changed=[])["dependency_key"]
    galaxy = repo.path.joinpath("galaxy.yml").read_text()
    repo.write("galaxy.yml", galaxy.replace("version: 0.0.0", "version: 0.1.0"))
    after = repo.plan(changed=[])["dependency_key"]

    # Every Release PR rewrites this line, and that same rewrite is what makes
    # the Release PR fan out to every role. Hashing the file would guarantee the
    # most expensive run in the repo always starts cold.
    assert before == after


def test_the_cache_key_changes_when_a_shipped_dependency_changes(repo):
    before = repo.plan(changed=[])["dependency_key"]
    galaxy = repo.path.joinpath("galaxy.yml").read_text()
    repo.write("galaxy.yml", galaxy.replace('"2.4.2"', '"2.5.0"'))

    assert repo.plan(changed=[])["dependency_key"] != before


def test_the_cache_key_changes_when_test_only_dependencies_change(repo):
    before = repo.plan(changed=[])["dependency_key"]
    repo.write(
        "extensions/molecule/requirements.yml",
        "---\ncollections:\n  - containers.podman\n  - community.general\n",
    )

    assert repo.plan(changed=[])["dependency_key"] != before


# --------------------------------------------------------------------------
# The weekly cold run
# --------------------------------------------------------------------------


def test_no_cache_is_threaded_through_to_every_job(repo):
    plan = repo.plan(changed=[], event="schedule", no_cache=True)

    assert plan["molecule"]
    assert all(job["no_cache"] is True for job in plan["molecule"])


def test_ordinary_runs_use_the_cache(repo):
    plan = repo.plan(changed=["roles/firewall/tasks/main.yml"])

    assert all(job["no_cache"] is False for job in plan["molecule"])


# --------------------------------------------------------------------------
# Job naming
# --------------------------------------------------------------------------


def test_job_names_identify_the_role_platform_and_core_version(repo):
    plan = repo.plan(changed=["roles/firewall/tasks/main.yml"])
    names = {job["name"] for job in plan["molecule"]}

    assert "firewall / el8 / core 2.16" in names
    assert "firewall / el10 / core 2.21" in names
