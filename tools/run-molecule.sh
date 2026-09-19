#!/usr/bin/env bash
# Run a role's Molecule scenario, locally, exactly the way CI runs it.
#
#   mise run molecule firewall                 every platform, every lane
#   mise run molecule firewall el9             one platform, every lane it has
#   mise run molecule firewall el9 --lane 2.16 one platform, one lane
#
# The role x platform x lane combinations come from tools/molecule_plan.py, the
# same table the workflow reads, so this cannot drift from CI.
#
# Requires rootless podman on a Linux host. It will not work in the devcontainer:
# podman needs a privileged outer container to run there, and a privileged
# container is the thing ADR 0002 refuses.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

role="${1:-}"
platform=""
lane=""

if [[ -z "$role" ]]; then
    echo "usage: mise run molecule <role> [platform] [--lane 2.16|current]" >&2
    exit 2
fi
shift

while [[ $# -gt 0 ]]; do
    case "$1" in
        --lane)
            lane="$2"
            shift 2
            ;;
        *)
            platform="$1"
            shift
            ;;
    esac
done

if ! command -v podman >/dev/null; then
    echo "podman is not installed. Rootless podman is the only Molecule engine," >&2
    echo "locally and in CI." >&2
    exit 1
fi

# The collection is installed rather than read from the working tree so that the
# scenario resolves the role by its real name, ohioit.roles.firewall, and so
# that the Shipped Dependencies a user would get are the ones under test.
echo "==> Building and installing the collection"
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT
uv run ansible-galaxy collection build --output-path "$build_dir" --force >/dev/null
uv run ansible-galaxy collection install "$build_dir"/ohioit-roles-*.tar.gz --force >/dev/null

echo "==> Installing Test-only Dependencies"
uv run ansible-galaxy collection install -r extensions/molecule/requirements.yml >/dev/null

jobs="$(
    uv run tools/molecule_plan.py --event push |
        python3 -c '
import json, sys
outputs = json.load(sys.stdin)
role, platform, lane = sys.argv[1:4]
for job in json.loads(outputs["molecule_matrix"])["include"]:
    if job["role"] != role:
        continue
    if platform and job["platform"] != platform:
        continue
    if lane and job["lane"] != lane:
        continue
    print(job["platform"], job["lane"], job["uv_project"])
' "$role" "$platform" "$lane"
)"

if [[ -z "$jobs" ]]; then
    echo "No Molecule jobs match role=$role platform=${platform:-any} lane=${lane:-any}." >&2
    echo "Check the role's meta/main.yml platforms and the tables in tools/molecule_plan.py." >&2
    exit 1
fi

status=0
while read -r platform_name lane_name uv_project; do
    echo
    echo "==> $role / $platform_name / lane $lane_name"
    if ! MOLECULE_PLATFORM="$platform_name" \
        uv run --project "$uv_project" molecule test --scenario-name "$role"; then
        status=1
        echo "!!! FAILED: $role / $platform_name / lane $lane_name" >&2
    fi
done <<<"$jobs"

exit "$status"
