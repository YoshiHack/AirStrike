"""
Shared module for AirStrike web interface.

This module contains shared variables, configurations, and utilities
used across the web interface components.
"""

import time
import logging
import threading
import subprocess
import os
from flask import Blueprint

# Set up logging
logger = logging.getLogger('airstrike')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Create Blueprint for shared routes
shared = Blueprint('shared', __name__)

# Configuration
config = {
    'interface': 'wlan0',
    'wordlist': '/usr/share/wordlists/rockyou.txt',
    'output_dir': './captures/',
    'sudo_password': '',  # Will be set by the user through the UI
    'sudo_configured': False  # Flag to track if sudo has been configured
}

# Attack state
attack_state = {
    'running': False,
    'attack_type': None,
    'target_network': None,
    'progress': 0,
    'log': [],
    'stop_event': None,
    'threads': []
}

# Statistics
stats = {
    'networks_count': 0,
    'attacks_count': 0,
    'captures_count': 0
}

def log_message(message):
    """
    Log a message to both the attack log and the application logger.
    
    Args:
        message (str): The message to log
    """
    timestamp = time.strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    attack_state['log'].append(formatted_message)
    logger.info(formatted_message)

def reset_attack_state():
    """
    Reset the attack state to default values.
    This should be called when an attack is stopped or fails.
    """
    attack_state['running'] = False
    attack_state['attack_type'] = None
    attack_state['progress'] = 0
    
    # Properly clean up threads and events
    if attack_state['stop_event'] and not attack_state['stop_event'].is_set():
        attack_state['stop_event'].set()
    
    # Create a new event for future attacks
    attack_state['stop_event'] = threading.Event()
    attack_state['threads'] = []

def run_with_sudo(command, password=None):
    """
    Run a command with sudo privileges.
    
    Args:
        command (str): The command to run
        password (str, optional): The sudo password. If None, uses the one in config
        
    Returns:
        tuple: (success, output, error)
    """
    try:
        # Use the password from config if not provided
        if password is None:
            password = config.get('sudo_password', '')
        
        # If no password is set, log a warning and try to run without sudo
        if not password and not config.get('sudo_configured', False):
            logger.warning("No sudo password configured. Attempting to run command without sudo.")
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            return process.returncode == 0, stdout, stderr
        
        # Run the command with sudo using the provided password
        process = subprocess.Popen(
            ['sudo', '-S'] + command.split(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Provide the password to sudo
        stdout, stderr = process.communicate(input=password + '\n')
        
        # Check if the command was successful
        success = process.returncode == 0
        
        # If the command failed, check for common sudo error messages
        if not success:
            stderr_lower = stderr.lower()
            if any(msg in stderr_lower for msg in ["incorrect password", "sorry, try again", "authentication failure"]):
                config['sudo_configured'] = False
                logger.error("Sudo authentication failed: Incorrect password")
                return False, stdout, "Incorrect sudo password"
        
        return success, stdout, stderr
    
    except Exception as e:
        logger.error(f"Error running command with sudo: {e}")
        return False, "", str(e)

def is_running_as_root():
    """
    Returns True if the current process is running as root (UID 0).
    """
    try:
        return os.geteuid() == 0
    except AttributeError:
        # Windows compatibility (no geteuid)
        return False

def can_run_sudo_without_password():
    """
    Returns True if the current user can run sudo without a password (NOPASSWD sudoers).
    """
    try:
        result = subprocess.run(['sudo', '-n', 'id', '-u'], capture_output=True, text=True)
        return result.returncode == 0 and result.stdout.strip() == '0'
    except Exception:
        return False

def is_sudo_authenticated():
    """
    Returns True if the user is authenticated for sudo (either running as root, sudo_configured is True, or can run sudo without password).
    """
    if is_running_as_root() or can_run_sudo_without_password():
        config['sudo_configured'] = True
        return True
    return config.get('sudo_configured', False)
    
    