#!/usr/bin/env bash
# Polymarket Reaper Bot v1.1 -- Linux/Mac launcher
# AC-38

set -e

# ---------------------------------------------------------------
# 1. Check Python 3.9+
# ---------------------------------------------------------------
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        major=$("$candidate" -c 'import sys; print(sys.version_info.major)')
        minor=$("$candidate" -c 'import sys; print(sys.version_info.minor)')
        if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.9+ is required but not found."
    echo "Please install Python 3.9 or later and try again."
    exit 1
fi

echo "Using $PYTHON (version $("$PYTHON" --version 2>&1))"

# ---------------------------------------------------------------
# 2. Install dependencies
# ---------------------------------------------------------------
echo "Installing dependencies..."
"$PYTHON" -m pip install -r requirements.txt --quiet

# ---------------------------------------------------------------
# 3. Start the bot
# ---------------------------------------------------------------
echo "Starting Polymarket Reaper Bot v1.1..."
"$PYTHON" src/main.py "$@"
