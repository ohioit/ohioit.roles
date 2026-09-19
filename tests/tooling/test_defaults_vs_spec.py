"""What the defaults-vs-spec check catches.

Both directions matter: a variable documented but never defaulted reads as
supported and isn't, and a variable defaulted but never documented is invisible
to anyone reading the role's README.
"""

from __future__ import annotations

import yaml


def write_role(repo, name: str, defaults: dict, options: dict) -> None:
    repo.add_role(name)
    repo.write(f"roles/{name}/defaults/main.yml", yaml.safe_dump(defaults))
    repo.write(
        f"roles/{name}/meta/argument_specs.yml",
        yaml.safe_dump({"argument_specs": {"main": {"options": options}}}),
    )


def test_agreement_passes(repo):
    write_role(
        repo,
        "agree",
        defaults={"foo": 1, "bar": "two"},
        options={"foo": {"type": "int"}, "bar": {"type": "str"}},
    )

    assert repo.check_defaults("agree").returncode == 0


def test_a_default_missing_from_the_spec_fails_and_names_it(repo):
    write_role(
        repo,
        "undocumented",
        defaults={"foo": 1, "bar": "two"},
        options={"foo": {"type": "int"}},
    )
    result = repo.check_defaults("undocumented")

    assert result.returncode == 1
    assert "`bar`" in result.stderr


def test_a_spec_option_with_no_default_fails_and_names_it(repo):
    write_role(
        repo,
        "undefaulted",
        defaults={"foo": 1},
        options={"foo": {"type": "int"}, "bar": {"type": "str"}},
    )
    result = repo.check_defaults("undefaulted")

    assert result.returncode == 1
    assert "`bar`" in result.stderr


def test_a_required_option_needs_no_default(repo):
    write_role(
        repo,
        "required",
        defaults={"foo": 1},
        options={"foo": {"type": "int"}, "bar": {"type": "str", "required": True}},
    )

    # Requiring a value and defaulting it are contradictory, so this is the one
    # asymmetry the check allows.
    assert repo.check_defaults("required").returncode == 0


def test_a_role_with_no_argument_spec_fails(repo):
    # The fixture role ships none, and every role is meant to.
    result = repo.check_defaults("firewall")

    assert result.returncode == 1
    assert "argument_specs.yml" in result.stderr


def test_every_role_is_checked_when_none_is_named(repo):
    write_role(repo, "agree", defaults={"foo": 1}, options={"foo": {"type": "int"}})
    result = repo.check_defaults()

    # The fixture "firewall" role has no spec, so checking everything must fail
    # even though the role named on its own would pass.
    assert result.returncode == 1
    assert "firewall" in result.stderr
