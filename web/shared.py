import time
from flask import Blueprint
shared = Blueprint('shared', __name__)
# Configuration
config = {
    'interface': 'wlan0',
    'wordlist': '/usr/share/wordlists/rockyou.txt',
    'output_dir': './captures/'
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
    timestamp = time.strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    attack_state['log'].append(formatted_message)
    shared.logger.info(formatted_message)
    
    