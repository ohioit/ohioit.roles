# Ohio University IT Roles Collection

[![Lint](https://github.com/ohioit/ohioit.roles/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/ohioit/ohioit.roles/actions/workflows/lint.yml)
[![Sanity](https://github.com/ohioit/ohioit.roles/actions/workflows/ansible-test.yml/badge.svg?branch=main)](https://github.com/ohioit/ohioit.roles/actions/workflows/ansible-test.yml)
[![Molecule](https://github.com/ohioit/ohioit.roles/actions/workflows/molecule.yml/badge.svg?branch=main)](https://github.com/ohioit/ohioit.roles/actions/workflows/molecule.yml)

`ohioit.roles` is the single Ansible collection where Ohio University IT keeps its
standard roles for managing Linux (RHEL) servers, and later Windows ones. It is the
only thing here that has a version: a change to any role ships in a collection
release, as a changelog entry naming that role.

## Included roles

| Role | Purpose |
| ---- | ------- |
| [`firewall`](roles/firewall/README.md) | Configure firewalld from a simple rule syntax, layered across common, group and host scopes, with pruning of objects the rules no longer declare. |

Each role's options are documented in its own README, generated from its
`meta/argument_specs.yml`.

## Requirements

- **ansible-core 2.16 or later.** 2.16 is the floor because it is the only
  ansible-core that manages a stock RHEL 8 host.
- **Target platforms**: RHEL 8, 9 and 10, and their rebuilds. Each role declares
  the platforms it supports in its own `meta/main.yml`, and CI tests it against
  every one of them.

The collection's own dependencies (`fedora.linux_system_roles`, `ansible.posix`)
are declared in `galaxy.yml` and install automatically with it.

## Using this collection

Install it from Ansible Galaxy:

```bash
ansible-galaxy collection install ohioit.roles
```

Or include it in a `requirements.yml`:

```yaml
---
collections:
  - name: ohioit.roles
```

Upgrade with `--upgrade`, or pin a version with `ohioit.roles:==0.1.0`. See
[using Ansible collections](https://docs.ansible.com/projects/ansible/devel/user_guide/collections_using.html)
for more detail.

```yaml
- hosts: servers
  roles:
    - role: ohioit.roles.firewall
```

## Support

Open an issue at <https://github.com/ohioit/ohioit.roles/issues>.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup, how to run the
tests, and what a pull request needs to pass. In short: a Conventional Commit
title, a changelog fragment when the change is user-facing, and green checks.

Repository settings that a maintainer applies by hand are recorded in
[`docs/github-repo-settings.md`](docs/github-repo-settings.md).

## Release notes

See the [changelog](CHANGELOG.md).

## Licensing

GNU General Public License v3.0 or later.

See [LICENSE](LICENSE) for the full text.
