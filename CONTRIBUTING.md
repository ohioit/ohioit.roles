# Contributing

## Development setup

The repository uses [mise](https://mise.jdx.dev/) to pin its tools and
[uv](https://docs.astral.sh/uv/) for Python environments.

```bash
mise install
uv sync
```

That gives you the `current` Core Lane — the newest ansible-core, on Python
3.14 — plus every lint and docs tool. The second Core Lane, ansible-core 2.16 on
Python 3.12, lives in `lanes/core-2.16/` and uv sets it up on demand; you do not
need to install anything for it.

## Tasks

| Command | What it does |
| --- | --- |
| `mise run test` | Tests for the repo's own tooling in `tools/` |
| `mise run lint` | ansible-lint, yamllint, antsibull-docs lint, defaults-vs-spec |
| `mise run docs` | Regenerate the options block in every role README |
| `mise run molecule <role> [platform] [--lane 2.16\|current]` | Run a role's scenario |
| `mise run changelog` | Lint the changelog fragments on your branch |

## Running the role tests

```bash
mise run molecule firewall             # every platform, every lane
mise run molecule firewall el9         # one platform, both its lanes
mise run molecule firewall el8 --lane 2.16
```

This needs **rootless podman** on a Linux host. It is the only engine, locally
and in CI, so "passes locally" means "passes in CI". Containers run with
`NET_ADMIN` and `NET_RAW` and never privileged, so no test container gets root
on the machine running it.

It does **not** work in the devcontainer: podman needs a privileged outer
container to run there, which is exactly what the engine choice rules out. The
devcontainer is for editing, linting and docs.

## Adding a role

1. Create `roles/<name>/` with the usual layout.
2. Declare its Target Platforms in `meta/main.yml` under
   `galaxy_info.platforms`. This is what CI tests it against — nothing in a
   workflow names a platform.
3. Write `meta/argument_specs.yml`. Every role ships one: it is the source the
   README options table is generated from, and ansible-lint requires it.
4. Start the README from `docs/role-readme-skeleton.md`, keeping the
   `BEGIN_ANSIBLE_DOCS` / `END_ANSIBLE_DOCS` markers, then run `mise run docs`.
5. Add a scenario at `extensions/molecule/<name>/` with a `molecule.yml`
   naming the scenario, a `converge.yml` and a `verify.yml`. Copy
   `extensions/molecule/firewall/` — the shared plumbing is inherited, so a
   scenario should be small.
6. `verify.yml` must assert **live state on the host**, by asking the system
   rather than re-reading the variables the role was given. Re-reading its own
   input passes whether or not anything reached the machine.

## Pull requests

**Title.** Conventional Commits, checked by CI. The title is what decides the
next version, so it is not decoration:

| Type | Effect on the version |
| --- | --- |
| `feat` | patch before 1.0, minor after |
| `fix`, `perf`, `revert` | patch |
| `!` or a `BREAKING CHANGE:` footer | minor before 1.0, major after |
| `docs`, `chore`, `ci`, `test`, `build`, `refactor`, `style` | no release |

Scope is optional. When a change touches one role, the scope is the role name:
`fix(firewall): stop pruning ssh when a rule renames it`.

**Changelog fragment.** Any change that moves the version needs one, under
`changelogs/fragments/<short-slug>.yml`:

```yaml
bugfixes:
  - firewall - stop pruning ssh when a rule renames the service.
```

Role entries name the role first, as in `firewall - stop pruning ssh`. A
maintainer can waive the requirement with
the `skip-changelog` label. Fragments are linted whether or not they are
required, so a `docs:` pull request that adds one still gets it checked.

**Checks.** Four required: `Lint Result`, `Sanity Result`, `Molecule Result`,
`PR Meta Result`. Each is a Result Job summarising a whole workflow, so the red X
is on the summary and the detail is in the job behind it.

On a pull request, Molecule runs only the roles you touched. Changing shared test
plumbing, `galaxy.yml` or either lane's lock file runs everything.

If role docs are out of date, CI regenerates and pushes them for you. On a fork
it cannot, so run `mise run docs` and commit the result.

## Where decisions live

- `docs/github-repo-settings.md` — settings a human applies by hand, and the
  one-time provisioning steps an agent cannot do for you.
- Comments, kept short, only where code looks redundant or wrong without them.
