#!/usr/bin/env bash
# Rebuild the environment from scratch, exactly the way CI does.
#
#   ./scripts/rebuild.sh            # reproduce uv.lock exactly
#   ./scripts/rebuild.sh --latest   # re-resolve simple-steps-core to its newest commit
#
# If this passes locally and fails in CI, the difference is the machine, not
# the environment -- which is the whole point of running the same steps here.

set -euo pipefail
cd "$(dirname "$0")/.."

MODE="locked"
[ "${1:-}" = "--latest" ] && MODE="latest"

export UV_NO_CACHE=1

echo "==> scrubbing"
rm -rf .venv .pytest_cache
find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

echo "==> installing the pinned interpreter"
uv python install

if [ "$MODE" = "latest" ]; then
  echo "==> re-resolving simple-steps-core to its newest commit"
  uv lock --upgrade-package simple-steps-core
  uv sync --all-groups
  echo "==> uv.lock changed as follows (commit this to pin the new version):"
  git diff --stat uv.lock || true
else
  echo "==> building from the lockfile"
  uv sync --locked --all-groups
fi

echo "==> verifying"
SHA=$(sed -n 's/.*simple-steps-core\.git?branch=main#\([0-9a-f]*\).*/\1/p' uv.lock | head -1)
echo "    library commit: ${SHA:-<unresolved>}"
uv run python -c "import simple_steps_core as m; print('    import OK ->', m.__file__)"

echo "==> tests"
uv run pytest tests -v

echo
echo "Environment rebuilt from scratch. Activate it with: source .venv/bin/activate"
