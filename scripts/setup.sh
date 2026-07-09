#!/usr/bin/env bash
#
# Setup script for LocalTUI-LM
#
# Usage:
#   bash scripts/setup.sh
#
# This will:
#   1. Create a Python virtual environment
#   2. Install dependencies
#   3. Download a small GGUF model (optional)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== LocalTUI-LM Setup ==="
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "  Done."
else
    echo "Virtual environment already exists."
fi

# Activate
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -e .
echo "  Done."

# Ask about model download
echo ""
echo "A small model is recommended for CPU-only use."
echo "Default: Qwen2.5-1.5B-Instruct (Q4_K_M, ~1GB)"
read -p "Download the default model now? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python scripts/download_model.py
    mkdir -p data/models
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "To run LocalTUI-LM:"
echo "  1. Activate environment: source venv/bin/activate"
echo "  2. Launch the app:       localtui-lm"
echo ""
echo "Or directly: python -m src.app.app"
