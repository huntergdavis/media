#!/bin/bash

# TUI Media Editor Launcher
# Activates virtual environment and runs the TUI editor

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
VENV_PATH="$SCRIPT_DIR/media_editor_env"
TUI_SCRIPT="$SCRIPT_DIR/media_tui.py"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}❌ Virtual environment not found at: $VENV_PATH${NC}"
    echo "Please run the setup first or install textual manually."
    exit 1
fi

# Check if TUI script exists
if [ ! -f "$TUI_SCRIPT" ]; then
    echo -e "${RED}❌ TUI script not found at: $TUI_SCRIPT${NC}"
    exit 1
fi

# Activate virtual environment and run the TUI
echo -e "${GREEN}🚀 Starting Physical Media TUI Editor...${NC}"

cd "$SCRIPT_DIR"
source "$VENV_PATH/bin/activate"

# Pass any command line arguments to the script
python3 "$TUI_SCRIPT" "$@"