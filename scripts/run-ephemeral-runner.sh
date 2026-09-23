#!/usr/bin/env bash
# Run the self-hosted runner in ephemeral mode: one job per registration.
#
# A normal self-hosted runner is a long-lived process on a machine that keeps
# its disk forever, so job N+1 inherits whatever job N left behind. Ephemeral
# mode fixes that: the runner accepts exactly one job, deregisters, and exits.
# This loop then wipes the work directory and registers a brand new runner.
#
#   ./scripts/run-ephemeral-runner.sh
#
# One-time PAT setup (needs `repo` scope; stored in the macOS keychain, not on
# disk in plaintext):
#   security add-generic-password -a "$USER" -s gh-runner-pat -w
#
# Stop with Ctrl-C. To run it unattended instead, see the launchd note at the
# bottom of this file.

set -euo pipefail

OWNER="stusynakowski"
REPO="simple_steps_test_running"
RUNNER_DIR="$HOME/actions-runner"
LABELS="macos-local"

if [ ! -x "$RUNNER_DIR/config.sh" ]; then
  echo "error: no runner at $RUNNER_DIR -- run ./scripts/setup-runner.sh first" >&2
  exit 1
fi

PAT=$(security find-generic-password -a "$USER" -s gh-runner-pat -w 2>/dev/null || true)
if [ -z "$PAT" ]; then
  echo "error: no PAT in the keychain." >&2
  echo "add one with: security add-generic-password -a \"\$USER\" -s gh-runner-pat -w" >&2
  exit 1
fi

cleanup() {
  echo
  echo "==> deregistering before exit"
  cd "$RUNNER_DIR"
  TOKEN=$(mint_token remove 2>/dev/null || true)
  [ -n "$TOKEN" ] && ./config.sh remove --token "$TOKEN" >/dev/null 2>&1 || true
  exit 0
}

mint_token() {
  # $1 is "registration" or "remove"
  curl -fsSL -X POST \
    -H "Authorization: Bearer ${PAT}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/${OWNER}/${REPO}/actions/runners/${1}-token" \
    | sed -nE 's/.*"token": *"([^"]+)".*/\1/p'
}

trap cleanup INT TERM

cd "$RUNNER_DIR"

# A service-installed runner would compete with this loop for jobs.
./svc.sh stop  >/dev/null 2>&1 || true
./svc.sh uninstall >/dev/null 2>&1 || true

echo "Ephemeral runner loop started. Ctrl-C to stop."

while true; do
  echo
  echo "==> wiping the work directory"
  rm -rf "$RUNNER_DIR/_work"

  # Clear any stale registration before taking a new one.
  ./config.sh remove --token "$(mint_token remove)" >/dev/null 2>&1 || true

  echo "==> registering a fresh ephemeral runner"
  ./config.sh \
    --url "https://github.com/${OWNER}/${REPO}" \
    --token "$(mint_token registration)" \
    --name "$(hostname -s)-ephemeral" \
    --labels "$LABELS" \
    --work _work \
    --unattended \
    --ephemeral \
    --replace

  echo "==> waiting for one job"
  ./run.sh || echo "   (runner exited non-zero; restarting)"

  echo "==> job finished; runner deregistered"
done

# To run this unattended, wrap it in a launchd agent rather than `svc.sh`
# (svc.sh installs the plain runner, which is what you are replacing):
#
#   ~/Library/LaunchAgents/com.simplesteps.ephemeral-runner.plist
#     ProgramArguments: /bin/bash <abs path to this script>
#     RunAtLoad: true
#     KeepAlive: true
#   launchctl load -w ~/Library/LaunchAgents/com.simplesteps.ephemeral-runner.plist
