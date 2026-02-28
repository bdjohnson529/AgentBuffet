#!/usr/bin/env bash
# Create and prepare a Python virtual environment for AgentBuffet scripts.
# Run from repo root: ./scripts/setup_venv.sh
# Or: bash scripts/setup_venv.sh

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
REQUIREMENTS="${REPO_ROOT}/scripts/requirements.txt"

cd "$REPO_ROOT"

if [ -d "$VENV_DIR" ]; then
  echo "Virtual environment already exists at $VENV_DIR"
  echo "To recreate it, remove it first: rm -rf .venv"
  exit 0
fi

echo "Creating virtual environment at $VENV_DIR"
python3 -m venv "$VENV_DIR"

echo "Activating and installing dependencies from scripts/requirements.txt"
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$REQUIREMENTS"

echo "Done. Activate the venv with: source .venv/bin/activate"
deactivate 2>/dev/null || true
