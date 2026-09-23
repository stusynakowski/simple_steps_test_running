#!/usr/bin/env bash
# Install and register a self-hosted GitHub Actions runner on this Mac.
#
#   ./scripts/setup-runner.sh <REGISTRATION_TOKEN>
#
# Get the token from:
#   https://github.com/stusynakowski/simple_steps_test_running/settings/actions/runners/new
# It is shown in the `./config.sh --token ...` line and expires after ~1 hour.

set -euo pipefail

REPO_URL="https://github.com/stusynakowski/simple_steps_test_running"
RUNNER_DIR="$HOME/actions-runner"
LABELS="macos-local"

TOKEN="${1:-${RUNNER_TOKEN:-}}"
if [ -z "$TOKEN" ]; then
  echo "error: no registration token." >&2
  echo "usage: $0 <REGISTRATION_TOKEN>" >&2
  echo "get one at ${REPO_URL}/settings/actions/runners/new" >&2
  exit 1
fi

# uv provides the Python interpreters the workflow builds against.
if ! command -v uv >/dev/null 2>&1; then
  echo "==> installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

if [ -d "$RUNNER_DIR" ]; then
  echo "==> $RUNNER_DIR already exists; reusing it"
else
  echo "==> downloading the latest runner for osx-arm64"
  mkdir -p "$RUNNER_DIR"
  VERSION=$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest \
    | sed -nE 's/.*"tag_name": *"v?([^"]+)".*/\1/p' | head -1)
  echo "    version ${VERSION}"
  curl -fL -o "$RUNNER_DIR/runner.tar.gz" \
    "https://github.com/actions/runner/releases/download/v${VERSION}/actions-runner-osx-arm64-${VERSION}.tar.gz"
  tar xzf "$RUNNER_DIR/runner.tar.gz" -C "$RUNNER_DIR"
  rm "$RUNNER_DIR/runner.tar.gz"
fi

cd "$RUNNER_DIR"

echo "==> registering with ${REPO_URL}"
./config.sh \
  --url "$REPO_URL" \
  --token "$TOKEN" \
  --name "$(hostname -s)-local" \
  --labels "$LABELS" \
  --work _work \
  --unattended \
  --replace

# Installs a launchd service so the runner survives logout and reboot.
echo "==> installing the runner as a background service"
./svc.sh install
./svc.sh start
./svc.sh status

echo
echo "Runner is up. Check it at ${REPO_URL}/settings/actions/runners"
echo "Control it with:  cd $RUNNER_DIR && ./svc.sh {start|stop|status|uninstall}"
