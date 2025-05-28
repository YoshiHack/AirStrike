"""
Network Scanner Module for discovering devices on the network
"""

import socket
import struct
import fcntl
import subprocess
import re
import threading
import time
from web.shared import log_message

def get_interface_ip(interface):
    """Get IP address of the specified interface"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', interface[:15].encode('utf-8'))
        )[20:24])
    except Exception as e:
        log_message(f"[-] Error getting interface IP: {str(e)}", "error")
        return None

def get_network_range(interface_ip):
    """Get network range from interface IP"""
    # Assuming /24 network for simplicity
    return '.'.join(interface_ip.split('.')[:-1]) + '.0/24'

def parse_arp_output(arp_output):
    """Parse arp-scan output to extract devices"""
    devices = []
    lines = arp_output.decode('utf-8').split('\n')
    
    for line in lines:
        try:
            # Skip empty lines and header
            if not line or 'Interface' in line or 'Starting' in line or 'Ending' in line:
                continue
                
            # Parse IP and MAC addresses
            match = re.match(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:]+)', line)
            if match:
                ip, mac = match.groups()
                
                # Try to get manufacturer from MAC address (first 3 octets)
                vendor = "Unknown"
                try:
                    mac_prefix = mac.replace(':', '').upper()[:6]
                    vendor = f"Device ({mac_prefix})"
                except:
                    pass
                    
                # Create device entry with default hostname
                device = {
                    'ip': ip,
                    'mac': mac,
                    'hostname': f"{vendor} at {ip}"  # Default hostname
                }
                
                # Try to get hostname with timeout
                try:
                    socket.setdefaulttimeout(1)  # 1 second timeout
                    hostname = socket.gethostbyaddr(ip)[0]
                    if hostname and hostname != ip:
                        device['hostname'] = hostname
                except:
                    # Keep using the default hostname on any error
                    pass
                
                devices.append(device)
                
        except Exception as e:
            log_message(f"[-] Error parsing device info: {str(e)}", "error")
            continue
    
    return devices

def scan_network(interface):
    """
    Scan network for active devices using arp-scan
    
    Args:
        interface: Network interface to scan on
        
    Returns:
        list: List of discovered devices with their IP, MAC, and hostname
    """
    try:
        # Get interface IP
        interface_ip = get_interface_ip(interface)
        if not interface_ip:
            raise Exception("Could not get interface IP")
            
        # Get network range
        network_range = get_network_range(interface_ip)
        
        log_message(f"[+] Starting network scan on {interface} ({network_range})")
        
        # Run arp-scan
        process = subprocess.Popen(
            ['arp-scan', '--interface', interface, network_range],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        output, error = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"arp-scan failed: {error.decode('utf-8')}")
            
        # Parse output
        devices = parse_arp_output(output)
        
        log_message(f"[+] Found {len(devices)} devices on the network")
        return devices
        
    except Exception as e:
        log_message(f"[-] Network scan error: {str(e)}", "error")
        return []

def start_continuous_scan(interface, callback, interval=30):
    """
    Start continuous network scanning
    
    Args:
        interface: Network interface to scan on
        callback: Function to call with scan results
        interval: Scan interval in seconds
    """
    def scan_thread():
        while True:
            devices = scan_network(interface)
            callback(devices)
            time.sleep(interval)
            
    thread = threading.Thread(target=scan_thread)
    thread.daemon = True
    thread.start()
    return thread 