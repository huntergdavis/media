#!/bin/bash

# TUI Media Editor Launcher
# Sets up the virtual environment (if needed) and runs the TUI editor

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
VENV_PATH="$SCRIPT_DIR/media_editor_env"
TUI_SCRIPT="$SCRIPT_DIR/media_tui.py"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if TUI script exists
if [ ! -f "$TUI_SCRIPT" ]; then
    echo -e "${RED}❌ TUI script not found at: $TUI_SCRIPT${NC}"
    exit 1
fi

# Pick a python interpreter
PYTHON="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON" ]; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.${NC}"
    exit 1
fi

# Create the virtual environment if it's missing
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}📦 Virtual environment not found — creating it...${NC}"
    if ! "$PYTHON" -m venv "$VENV_PATH"; then
        # Clean up the partial venv so the next run retries from scratch
        rm -rf "$VENV_PATH"
        echo -e "${RED}❌ Failed to create the virtual environment.${NC}"
        echo "On Debian/Ubuntu you may need the venv package, e.g.:"
        echo "    sudo apt install python3-venv"
        exit 1
    fi
fi

# Activate it
source "$VENV_PATH/bin/activate"

# Install/verify dependencies if textual is missing
if ! python -c "import textual" &> /dev/null; then
    echo -e "${YELLOW}⬇️  Installing dependencies (textual)...${NC}"
    pip install --quiet --upgrade pip
    if [ -f "$REQUIREMENTS" ]; then
        pip install --quiet -r "$REQUIREMENTS"
    else
        pip install --quiet textual
    fi
    echo -e "${GREEN}✅ Dependencies installed.${NC}"
fi

# Run the TUI
echo -e "${GREEN}🚀 Starting Physical Media TUI Editor...${NC}"

cd "$SCRIPT_DIR"

# Pass any command line arguments to the script
python "$TUI_SCRIPT" "$@"
