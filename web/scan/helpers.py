import os
import sys
from web.shared import *
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from utils.network_utils import run_scan

def scan_wifi_networks():
    """
    Scan for available WiFi networks using the configured interface.
    
    Returns:
        list: List of network dictionaries, or empty list if an error occurs.
    """
    try:
        networks = run_scan(config['interface'])
        # Update stats
        stats['networks_count'] = len(networks)
        return networks, None
    except Exception as e:
        return [], str(e) 