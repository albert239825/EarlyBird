#!/bin/bash

# Start EarlyBird - Backend and Frontend in separate Terminal windows
# This script opens two Terminal windows: one for backend, one for frontend

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting EarlyBird in separate Terminal windows...${NC}"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Backend command: deactivate conda if active, activate .venv, then run backend
BACKEND_CMD="cd '$SCRIPT_DIR' \
&& if [ -x '.venv/bin/python' ]; then .venv/bin/python -m backend.app; else echo 'Missing .venv/bin/python' && exit 1; fi; \
echo ''; echo 'Backend exited with code '$?'. Press enter to close...'; read"

# Frontend command: navigate to client/early-bird and run next dev
FRONTEND_CMD="cd '$SCRIPT_DIR/client/early-bird' && npx next dev -p 3000"

# Open backend in a new Terminal window
echo -e "${BLUE}Opening backend Terminal window...${NC}"
osascript <<APPLESCRIPT
tell application "Terminal"
    set backendWindow to do script "$BACKEND_CMD"
    set custom title of backendWindow to "EarlyBird - Backend"
end tell
APPLESCRIPT

# Wait a moment before opening the second window
sleep 1

# Open frontend in a new Terminal window
echo -e "${BLUE}Opening frontend Terminal window...${NC}"
osascript <<APPLESCRIPT
tell application "Terminal"
    set frontendWindow to do script "$FRONTEND_CMD"
    set custom title of frontendWindow to "EarlyBird - Frontend"
end tell
APPLESCRIPT

echo -e "${GREEN}✓ Both Terminal windows have been opened!${NC}"
echo -e "${GREEN}  Backend is running in the first Terminal window${NC}"
echo -e "${GREEN}  Frontend is running in the second Terminal window${NC}"
