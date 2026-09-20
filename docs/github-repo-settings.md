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

- [ ] **Create a GitHub App** in the `ohioit` org and install it on this
      repository. It needs `contents: write` and `pull-requests: write`.
      Store its app ID as the repository variable `APP_ID` and its private key
      as the secret `APP_PRIVATE_KEY`.

  > **Needs an org owner.** Creating an App is an organisation-level permission,
  > so this is the item to hand to someone who has it if you do not. It is also
  > the only blocker for the release pipeline.
  >
  > **Until it exists**, `release-please.yml` fails on every push to `main` and
  > `role-docs.yml` fails on every pull request. Both are expected and neither
  > is a Required Check, so merging still works — but they are red, and a red
  > check people learn to ignore is worse than no check. Do this before the
  > habit sets in.

  Used by `release-please.yml` and `role-docs.yml`. A push made with the stock
  `GITHUB_TOKEN` does not start workflows, so without the App the Release PR
  would sit with no checks and could never satisfy the Required Checks.
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

- [ ] **Allow squash merging only.** Turn off merge commits and rebase merging.
      Release-please reads the history on `main` as one commit per pull request.
- [ ] **Squash merge commit message: "Pull request title and description".**

  > This one is load-bearing and its default is wrong for us. On GitHub's
  > default setting the squashed commit's subject is `<PR title> (#123)` built
  > from a different source, and release-please reads the wrong subject: version
  > bumps stop happening, silently and with no failing check. If bumps ever stop,
  > check this first.

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
      `main`; the Release PR merges through the normal path like anything else.

Deliberately **not** enabled:

- **Require signed commits** — breaks local contributors for no gain here.
- **Require branches to be up to date before merging**, and **merge queue**. At
  this merge volume the stale-branch risk is small, and `push: main` plus the
  weekly Molecule run catch the rare semantic conflict. Revisit both together if
  merge volume makes it hurt.

Consequence accepted: the Release PR and every Renovate pull request need a
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
- The `role-docs.yml` auto-commit — it depends on a secret forks never get, and
  its push could dismiss a fresh approval. The docs *gate* is `docs-current`
  inside `Lint Result`, which needs no token.
- `release-please` and `publish` — neither runs on a pull request.

## Environments

- [ ] **`galaxy`** — holds `ANSIBLE_GALAXY_API_KEY`. Restrict to tags. No
      required reviewer for now; add one when publishing becomes automatic.

## The first release must be 0.1.0

Check this once, on the first Release PR release-please opens, and then never
again.

The manifest starts at `0.0.0` and `bump-patch-for-minor-pre-major` makes a
`feat` a patch, so left alone the first release would be `0.0.1`. A
`Release-As: 0.1.0` footer is already in the commit that declared the supported
range, which should be enough.

If the first Release PR says `0.0.1` anyway, force it:

```bash
git switch main && git pull
git commit --allow-empty -m "chore: force the first release" -m "Release-As: 0.1.0"
git push
```

`1.0.0` stays a deliberate declaration of stability, made later and on purpose.

## Variables

- `APP_ID` — the GitHub App's ID.
- `GALAXY_PUBLISH_ENABLED` — **leave unset.** Setting it to `true` is what turns
  on automatic publishing on release. Until then `publish-galaxy.yml` runs only
  when someone starts it by hand.
