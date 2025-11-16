#!/bin/bash

# This script creates or activates the virtual environment,
# installs dependencies, kills any process on port 8080,
# and runs the local server.

# --- Configuration ---
VENV_DIR="venv"
PORT=8080

# --- Check for virtual environment ---
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# --- Activate virtual environment ---
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# --- Install dependencies ---
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# --- Kill process on port ---
echo "Checking for process on port $PORT..."
PID=$(lsof -t -i:$PORT)
if [ -n "$PID" ]; then
    echo "Killing process $PID on port $PORT..."
    kill -9 "$PID"
fi

# --- Run the server ---
echo "Starting the server..."
python app.py 2>&1 | tee app.log
