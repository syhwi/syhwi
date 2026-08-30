#!/usr/bin/env bash
# Idempotent setup for the documentation preview environment.
# Creates a local virtualenv and installs the Markdown rendering dependencies.
set -euo pipefail

cd "$(dirname "$0")/.."

# Ensure the stdlib venv/ensurepip support is available (missing on some
# minimal Debian/Ubuntu images).
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y python3-venv >/dev/null
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

echo "Documentation preview environment is ready."
