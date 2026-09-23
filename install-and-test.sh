#!/usr/bin/env bash
# Install simple-steps-core into this environment, run the full test bed, and
# print an overview of what works, what is broken, and overall coverage.
#
#   ./install-and-test.sh              # install from the lockfile, test, report
#   ./install-and-test.sh --latest     # re-resolve to the library's newest commit
#   ./install-and-test.sh --no-install # environment already built; just test
#   ./install-and-test.sh --quiet      # only the final overview
#
# Exit codes:
#   0  everything passed
#   1  a check failed (tests, capability regression, or example divergence)
#   2  the environment could not be built
#
# Safe to re-run. Nothing outside this directory and uv's own caches is touched.

set -uo pipefail
cd "$(dirname "$0")"

MODE="locked"
DO_INSTALL=1
QUIET=0

for arg in "$@"; do
  case "$arg" in
    --latest)     MODE="latest" ;;
    --no-install) DO_INSTALL=0 ;;
    --quiet|-q)   QUIET=1 ;;
    --help|-h)    sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $arg (try --help)" >&2; exit 2 ;;
  esac
done

if [ -t 1 ]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; RED=$'\033[31m'
  YELLOW=$'\033[33m'; RESET=$'\033[0m'
else
  BOLD=""; DIM=""; GREEN=""; RED=""; YELLOW=""; RESET=""
fi

step()  { [ "$QUIET" = 1 ] || printf '\n%s==> %s%s\n' "$BOLD" "$1" "$RESET"; }
note()  { [ "$QUIET" = 1 ] || printf '    %s%s%s\n' "$DIM" "$1" "$RESET"; }
ok()    { [ "$QUIET" = 1 ] || printf '    %s✓%s %s\n' "$GREEN" "$RESET" "$1"; }
warn()  { printf '    %s!%s %s\n' "$YELLOW" "$RESET" "$1" >&2; }
fail()  { printf '    %s✗%s %s\n' "$RED" "$RESET" "$1" >&2; }

# Run a command, keeping its output only if it fails. Test output is noise
# when everything passes and the only thing you want when it does not.
run_quietly() {
  local label="$1"; shift
  local log; log="$(mktemp)"
  if "$@" >"$log" 2>&1; then
    ok "$label"
    rm -f "$log"
    return 0
  fi
  fail "$label"
  echo
  cat "$log" >&2
  rm -f "$log"
  return 1
}

# ── 0. preflight ─────────────────────────────────────────────────────────
step "checking prerequisites"

if ! command -v uv >/dev/null 2>&1; then
  fail "uv is not installed."
  echo
  echo "    uv manages both the Python interpreter and the dependencies here." >&2
  echo "    Install it with one of:" >&2
  echo "      brew install uv" >&2
  echo "      curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 2
fi
ok "uv $(uv --version | awk '{print $2}')"

# A VIRTUAL_ENV pointing somewhere else makes uv print a warning on every
# command. Clearing it for this script is quieter than explaining it.
if [ -n "${VIRTUAL_ENV:-}" ] && [ "${VIRTUAL_ENV}" != "$PWD/.venv" ]; then
  note "ignoring active venv at ${VIRTUAL_ENV}"
  unset VIRTUAL_ENV
fi

# ── 1. build the environment ─────────────────────────────────────────────
if [ "$DO_INSTALL" = 1 ]; then
  step "installing the pinned interpreter"
  run_quietly "python $(cat .python-version)" uv python install || exit 2

  if [ "$MODE" = "latest" ]; then
    step "re-resolving simple-steps-core to its newest commit"
    run_quietly "lock updated" uv lock --upgrade-package simple-steps-core || exit 2
    run_quietly "environment synced" uv sync --all-groups || exit 2
    if ! git diff --quiet uv.lock 2>/dev/null; then
      warn "uv.lock changed — commit it to pin this version"
    fi
  else
    step "installing simple-steps-core and test dependencies"
    # --locked refuses to proceed if uv.lock has drifted from pyproject.toml,
    # so this can never quietly install a different set of versions than CI.
    if ! run_quietly "environment built from uv.lock" \
         uv sync --locked --all-groups; then
      warn "if the lockfile is stale, run: uv lock && uv sync --all-groups"
      exit 2
    fi
  fi
else
  step "skipping install (--no-install)"
fi

# ── 2. verify it installed as a real consumer install ────────────────────
step "verifying the install"

if ! uv run python -c "import simple_steps_core" >/dev/null 2>&1; then
  fail "simple_steps_core does not import"
  uv run python -c "import simple_steps_core" 2>&1 | tail -20 >&2
  exit 2
fi
ok "simple_steps_core imports"

if [ "$QUIET" = 0 ]; then
  uv run python -m capability.provenance 2>/dev/null | sed 's/^/    /'
fi

# The whole point of this repo is that it tests a built artifact. An editable
# install would silently follow the library's source tree instead.
if uv pip list --format=json 2>/dev/null | grep -q '"editable_project_location"'; then
  fail "an editable install leaked in — this must test a built artifact"
  exit 2
fi

# ── 3. the three checks, in CI order ─────────────────────────────────────
STATUS=0

step "running the test suite"
run_quietly "pytest" uv run pytest || STATUS=1

step "checking for capability regressions"
if [ -f capability_baseline.json ]; then
  run_quietly "no capability regressed" \
    uv run python scripts/check-baseline.py || STATUS=1
else
  note "no baseline yet — creating one from this run"
  uv run python scripts/check-baseline.py --update >/dev/null 2>&1 \
    && ok "baseline created" || warn "could not create a baseline"
fi

step "comparing examples against plain Python"
run_quietly "every example matches its plain-Python oracle" \
  uv run python compare.py || STATUS=1

# ── 4. the overview ──────────────────────────────────────────────────────
echo
uv run python -m capability.summary || STATUS=1

if [ "$STATUS" = 0 ]; then
  printf '%s  all checks passed%s\n\n' "$GREEN" "$RESET"
else
  printf '%s  some checks failed — see the output above%s\n\n' "$RED" "$RESET"
fi
exit "$STATUS"
