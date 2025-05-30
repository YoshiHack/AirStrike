# AirStrike/config.py
import os

# --- Project Root Definition ---
# The directory where this config.py file is located is the project root.
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# --- Core Application Settings ---
DEFAULT_INTERFACE = 'wlan0'  # Default wireless interface to use
DEFAULT_WORDLIST = '/usr/share/wordlists/rockyou.txt'  # Common path on Kali

# --- Output Directory for Captures and Logs ---
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'captures')
# Attempt to create the output directory if it doesn't exist
try:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
except OSError as e:
    print(f"Warning: Could not create output directory {OUTPUT_DIR}: {e}")
    # Depending on the importance, you might want to exit or handle this differently.
    pass

# --- Flask Specific Configuration ---
SECRET_KEY = os.urandom(32)  # Strong secret key for session management, CSRF, etc.
DEBUG = True  # Enables Flask debug mode. SET TO FALSE IN PRODUCTION!
# Other Flask config: e.g., SESSION_COOKIE_SECURE = True (for HTTPS in production)

# --- Logging Configuration ---
# Basic logging level for the application. Can be overridden by Flask app logger settings.
LOG_LEVEL = 'INFO'  # Options: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'

# --- Application Behavior Settings ---
DEFAULT_SCAN_DURATION = 30  # Default duration for network scans in seconds
DEFAULT_ATTACK_TIMEOUT = 600  # Default timeout for long-running attacks (e.g., 10 minutes)
MAX_LOG_LINES_MEMORY = 200 # Max attack log lines to keep in memory for polling

# --- Paths to External Tools (if not in system PATH or need specific versions) ---
# Example:
# TSHARK_PATH = '/usr/bin/tshark'
# AIRCRACK_NG_PATH = '/usr/sbin/aircrack-ng'

# --- Print statements for verification during startup (optional) ---
print(f"CONFIG_LOADED: Project Root determined as: {PROJECT_ROOT}")
print(f"CONFIG_LOADED: Output Directory set to: {OUTPUT_DIR}")
print(f"CONFIG_LOADED: Default Interface: {DEFAULT_INTERFACE}")
print(f"CONFIG_LOADED: Flask DEBUG mode: {DEBUG}")

