# airstrike/config.py
import os

# Core Settings
DEFAULT_INTERFACE = 'wlan0'
DEFAULT_WORDLIST = '/usr/share/wordlists/rockyou.txt'
OUTPUT_DIR = os.path.join(os.getcwd(), 'captures') # Ensure absolute path if needed

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Flask Specific Config
SECRET_KEY = os.urandom(24)
DEBUG = True # Set to False in production