#!/usr/bin/env bash
set -euo pipefail
# Launch the AI-EDA Playground Web UI
# Usage: ./launch_ui.sh [--port 7860] [--host 127.0.0.1] [--share]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

# Auto-create venv if missing
if [ ! -d "$VENV" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" --quiet
fi

echo "🔬 Starting AI-EDA Playground Web UI..."
"$VENV/bin/python" -m src.cli webui "$@"
