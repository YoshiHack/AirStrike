#!/bin/bash

# Check if script is already running as root
if [ "$EUID" -ne 0 ]; then
    echo "AirStrike requires root privileges for deauthentication attacks."
    echo "Please enter your password to run AirStrike with sudo:"
    # Re-run the script with sudo
    exec sudo "$0" "$@"
    exit $?
fi

echo "Starting AirStrike with root privileges..."
echo "Deauthentication attacks should now work properly."

# Make sure the Python environment is preserved when using sudo
# Set up Python path
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Run with Python available in PATH
python run.py 