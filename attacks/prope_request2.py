# Fixed version of the Perl-based probe request sniffer rewritten in Python
# prope_request2.py

import os
import re
import signal
import subprocess
import time
import argparse
from collections import defaultdict

# Global variables
detected_ssids = defaultdict(lambda: [0, '', 0])
unique_ssid_count = 0
dump_file = None
verbose = False


def handle_signal(sig, frame):
    print("\n[!] Signal received. Dumping SSIDs...")
    dump_networks()
    exit(0)

def dump_networks():
    global detected_ssids
    print("\n--- Detected SSIDs ---")
    print(f"{'MAC Address':<20} {'SSID':<30} {'Count':<10} {'Last Seen'}")
    print("-" * 80)
    with open(dump_file, 'w') if dump_file else open(os.devnull, 'w') as f:
        for ssid, (count, mac, last_seen) in detected_ssids.items():
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_seen))
            line = f"{mac:<20} {ssid:<30} {count:<10} {timestamp}"
            print(line)
            if dump_file:
                f.write(line + "\n")
        print(f"Total unique SSIDs: {len(detected_ssids)}")


def main(interface, tshark_path):
    global detected_ssids, unique_ssid_count, dump_file, verbose

    try:
        process = subprocess.Popen(
            [tshark_path, '-i', interface, '-n', '-l', 'subtype', 'probereq'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True
        )

        ssid_regex = re.compile(r"([a-zA-Z0-9:]{17}).+SSID=([^\r\n]+)")

        for line in process.stdout:
            match = ssid_regex.search(line)
            if match:
                mac = match.group(1).strip()
                ssid = match.group(2).strip()

                if ssid.lower() == "broadcast" or ssid == "":
                    continue

                if ssid not in detected_ssids:
                    unique_ssid_count += 1
                    print(f"[+] New probe from {mac} for SSID: {ssid} [{unique_ssid_count}]")
                else:
                    if verbose:
                        print(f"[-] Repeated probe: {ssid}")

                detected_ssids[ssid][0] += 1  # Count
                detected_ssids[ssid][1] = mac  # MAC
                detected_ssids[ssid][2] = time.time()  # Timestamp

    except KeyboardInterrupt:
        handle_signal(None, None)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    parser = argparse.ArgumentParser(description='Wi-Fi Probe Request Sniffer')
    parser.add_argument('--interface', default='wlan0', help='Wireless interface (in monitor mode)')
    parser.add_argument('--tshark-path', default='/usr/bin/tshark', help='Path to tshark binary')
    parser.add_argument('-d', '--dump', help='Save results to file')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()

    dump_file = args.dump
    verbose = args.verbose

    print("\n[*] Starting Probe Request Sniffer")
    print(f"[*] Interface: {args.interface}\n[*] TShark: {args.tshark_path}")
    if dump_file:
        print(f"[*] Output will be saved to {dump_file}")

    main(args.interface, args.tshark_path)
