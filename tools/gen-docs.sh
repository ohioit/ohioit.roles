#!/usr/bin/env bash
# Regenerate the marked options block in every role README.
#
# Called by `mise run docs` locally, by the docs-current gate in lint.yml, and
# by the auto-commit job in role-docs.yml. One script so the three cannot
# disagree about what "current" means -- if they could, the gate would fail on
# work the auto-commit had just done.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TEMPLATE="tools/aar-doc-template.md.j2"

for role_path in roles/*/; do
    role="$(basename "$role_path")"
    [[ -d "$role_path/tasks" ]] || continue

    if [[ ! -f "$role_path/README.md" ]]; then
        echo "error: roles/$role has no README.md." >&2
        echo "Start from the skeleton in docs/role-readme-skeleton.md." >&2
        exit 1
    fi

    # aar-doc replaces the marker lines themselves, so a README without them
    # cannot be injected into. It exits non-zero and says which marker is
    # missing; this check just names the role first, since aar-doc only knows
    # about the file it was handed.
    if ! grep -q "BEGIN_ANSIBLE_DOCS" "$role_path/README.md"; then
        echo "error: roles/$role/README.md has no <!-- BEGIN_ANSIBLE_DOCS --> marker." >&2
        echo "Copy the markers from docs/role-readme-skeleton.md." >&2
        exit 1
    fi

    echo "==> roles/$role"
    uv run aar-doc \
        --output-mode inject \
        --output-template "$TEMPLATE" \
        "$role_path" markdown
done
