# GitHub repository settings

Settings a human applies in the GitHub UI, recorded here because they are not
code and cannot be. This file is the source of truth: when something drifts,
re-read this and re-apply it.

Deliberately not a script. Driving rulesets through `gh api` is fiddly, needs an
admin token the repository otherwise has no use for, and drifts from what an
admin actually clicks.

## One-time provisioning

Steps an agent cannot do. Until these are done, the checks that depend on them
fail.

> **No GitHub App is needed.** Releases are cut by a maintainer running
> `mise run release`, which opens an ordinary pull request from their own
> credentials. CI only tags and publishes after it merges, which the stock
> `GITHUB_TOKEN` can do. See CONTRIBUTING.md for the three steps.

- [ ] **Create the `skip-changelog` label.** Labels are created by hand; there is
      no labels-as-code sync. The five labels `.github/labeler.yml` manages
      (`actions`, `devcontainer`, `documentation`, `roles`, `firewall`) already
      exist.
- [ ] **Create the `weekly-failure` label**, used by the weekly Molecule run's
      tracking issue.
- [ ] **Create a dedicated Galaxy service account** that owns the `ohioit`
      namespace, and store its API key as `ANSIBLE_GALAXY_API_KEY` in the
      `galaxy` environment. Not needed until publishing is turned on.

## Merge settings

- [ ] **Allow squash merging only.** Turn off merge commits and rebase merging,
      so `main` reads as one commit per pull request.
- [ ] **Squash merge commit message: "Pull request title and description".**

  > Both are readability preferences, not requirements. Nothing parses commit
  > subjects to pick a version -- a person sets it in `galaxy.yml` when cutting
  > the release -- so merge commits break nothing.

- [ ] Automatically delete head branches after merge. (Optional, just tidy.)

## The `main` ruleset

- [ ] Require a pull request before merging.
    - [ ] **1 approval.**
    - [ ] Require review from Code Owners (`.github/CODEOWNERS`).
    - [ ] Dismiss stale approvals when new commits are pushed.
    - [ ] Require conversation resolution before merging.
- [ ] Require status checks to pass — exactly these four, and no others:
    - `Lint Result`
    - `Sanity Result`
    - `Molecule Result`
    - `PR Meta Result`
- [ ] Require linear history.
- [ ] Block force pushes.
- [ ] Restrict deletions.
- [ ] **Empty bypass list.** The App pushes to pull request branches, never to
      `main`; the release pull request merges through the normal path like anything else.

Deliberately **not** enabled:

- **Require signed commits** — breaks local contributors for no gain here.
- **Require branches to be up to date before merging**, and **merge queue**. At
  this merge volume the stale-branch risk is small, and `push: main` plus the
  weekly Molecule run catch the rare semantic conflict. Revisit both together if
  merge volume makes it hurt.

Consequence accepted: the release pull request and every Renovate pull request need a
teammate's approval.

## Why the required list is exactly four names

Each is a Result Job: the single job a workflow ends in, which passes only when
every job it depends on either succeeded or was skipped by design. Required
checks are matched by **job name**, not workflow name, so those four names are
unique across the repository and fixed for its life.

Adding a role, adding a lint tool, or moving the current Core Lane from 2.21 to
2.22 changes the jobs *behind* a Result Job and never this list. That matters
because this list is maintained by hand.

Not required, on purpose:

- `Labeler` — needs `pull-requests: write`, so it fails on fork pull requests by
  design.
- There is no docs auto-commit. The docs *gate* is `docs-current` inside
  `Lint Result`, which needs no token; contributors run `mise run docs`.
- `Release` — does not run on a pull request.

## Environments

- [ ] **`galaxy`** — holds `ANSIBLE_GALAXY_API_KEY`. Restrict to tags. No
      required reviewer for now; add one when publishing becomes automatic.

## Cutting a release

1. Set `version:` in `galaxy.yml`.
2. `mise run release` — collects the changelog fragments.
3. Commit both, push, open a pull request.

Merging it tags the version and publishes the GitHub Release with the tarball.
See CONTRIBUTING.md for how to choose the version. The first release is `0.1.0`;
`1.0.0` stays a deliberate declaration of stability.

## Variables

- `GALAXY_PUBLISH_ENABLED` — **leave unset.** Setting it to `true` is what turns
  on automatic publishing on release. Until then `publish-galaxy.yml` runs only
  when someone starts it by hand.
