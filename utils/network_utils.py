# AirStrike/utils/network_utils.py
import subprocess
import re
import sys
import os  # For os.geteuid()
import time # For time.sleep()
# from scapy.all import sniff, Dot11ProbeReq, Dot11Elt # Uncomment if using Scapy for sniffing

# --- Configuration (can be moved to main config.py if preferred) ---
COMMAND_TIMEOUT = 45  # Default timeout for subprocess commands in seconds

# --- System Command Execution with sudo ---
def run_with_sudo(command_str, timeout=COMMAND_TIMEOUT):
    """
    Executes a command string, ensuring it runs with sudo if the script isn't already root.
    Splits the command_str into a list for Popen.
    Args:
        command_str (str): The command to execute (e.g., "ip link show wlan0").
        timeout (int): Timeout for the command execution.
    Returns:
        tuple: (success_bool, stdout_str, stderr_str)
    """
    if not isinstance(command_str, str):
        print(f"ERROR (run_with_sudo): Command must be a string, got {type(command_str)}")
        return False, "", "Command must be a string."

    command_list = command_str.split()
    if not command_list:
        return False, "", "Empty command string provided."

    # Prepend 'sudo' if the script is not already running as root
    # AND 'sudo' is not already the first part of the command.
    is_root = os.geteuid() == 0
    if not is_root and command_list[0] != 'sudo':
        command_list.insert(0, 'sudo')
    elif is_root and command_list[0] == 'sudo': # Already root, remove redundant sudo
        command_list.pop(0)
        if not command_list: # If command was just "sudo"
             return False, "", "Empty command after removing sudo (was command just 'sudo'?)"


    # print(f"DEBUG (run_with_sudo): Executing: {' '.join(command_list)}") # Verbose
    try:
        process = subprocess.Popen(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, # Decodes stdout/stderr to strings
            universal_newlines=True # Ensures text mode across platforms
        )
        stdout, stderr = process.communicate(timeout=timeout)
        success = process.returncode == 0

        if not success:
            # print(f"DEBUG (run_with_sudo): Command failed (ret: {process.returncode}): {' '.join(command_list)}")
            # print(f"DEBUG (run_with_sudo): STDERR: {stderr.strip()}")
            # print(f"DEBUG (run_with_sudo): STDOUT: {stdout.strip()}")
            pass # Logging handled by caller or higher level service

        return success, stdout.strip(), stderr.strip()

    except subprocess.TimeoutExpired:
        print(f"ERROR (run_with_sudo): Command '{' '.join(command_list)}' timed out after {timeout}s.")
        if process: process.kill() # Ensure the process is killed
        return False, "", f"Command timed out after {timeout} seconds."
    except FileNotFoundError:
        print(f"ERROR (run_with_sudo): Command not found: '{command_list[0]}'. Ensure it's installed and in PATH.")
        return False, "", f"Command not found: {command_list[0]}"
    except Exception as e:
        print(f"ERROR (run_with_sudo): Exception running '{' '.join(command_list)}': {e}")
        return False, "", str(e)


# --- Wireless Interface Mode Management ---
def is_monitor_mode(interface_name):
    """Checks if the specified interface is currently in monitor mode."""
    # print(f"DEBUG (is_monitor_mode): Checking mode for {interface_name}")
    # Try 'iw dev <iface> info' first, as it's more reliable for mode detection
    success_iw, output_iw, err_iw = run_with_sudo(f"iw dev {interface_name} info")
    if success_iw and output_iw:
        if "type monitor" in output_iw.lower():
            # print(f"DEBUG (is_monitor_mode): {interface_name} is in monitor mode (via iw dev).")
            return True
        # If 'type managed' or other types are found, it's not monitor mode
        if "type managed" in output_iw.lower() or "type station" in output_iw.lower():
            # print(f"DEBUG (is_monitor_mode): {interface_name} is NOT in monitor mode (via iw dev - found other type).")
            return False
    else:
        # print(f"DEBUG (is_monitor_mode): 'iw dev {interface_name} info' failed or no output. Error: {err_iw}. Falling back to iwconfig.")
        pass

    # Fallback to 'iwconfig' if 'iw dev' fails or doesn't give a clear mode
    success_iwconfig, output_iwconfig, err_iwconfig = run_with_sudo(f"iwconfig {interface_name}")
    if success_iwconfig and output_iwconfig:
        if "Mode:Monitor" in output_iwconfig:
            # print(f"DEBUG (is_monitor_mode): {interface_name} is in monitor mode (via iwconfig).")
            return True
    else:
        # print(f"DEBUG (is_monitor_mode): 'iwconfig {interface_name}' failed or no output. Error: {err_iwconfig}")
        pass
    
    # print(f"DEBUG (is_monitor_mode): {interface_name} is NOT in monitor mode (checked iw dev and iwconfig).")
    return False


def _set_interface_mode_generic(interface_name, target_mode_iw, target_mode_iwconfig, check_success_func):
    """Generic helper to set interface mode, trying 'iw' then 'iwconfig'."""
    print(f"INFO: Attempting to set interface '{interface_name}' to mode for '{target_mode_iw}'.")
    
    # 1. Bring interface down
    run_with_sudo(f"ifconfig {interface_name} down")
    time.sleep(0.5) # Small delay for interface to go down

    # 2. Try setting mode with 'iw dev' (modern)
    cmd_iw = f"iw dev {interface_name} set type {target_mode_iw}"
    success_iw, _, err_iw = run_with_sudo(cmd_iw)

    if not success_iw:
        print(f"Warning: Command '{cmd_iw}' failed: {err_iw}. Trying 'iwconfig' as fallback.")
        # 3. Try setting mode with 'iwconfig' (legacy)
        cmd_iwconfig = f"iwconfig {interface_name} mode {target_mode_iwconfig}"
        success_iwconfig, _, err_iwconfig = run_with_sudo(cmd_iwconfig)
        if not success_iwconfig:
            print(f"ERROR: Command '{cmd_iwconfig}' also failed: {err_iwconfig}.")
            # Attempt to bring interface up anyway before returning failure
            run_with_sudo(f"ifconfig {interface_name} up")
            return False

    # 4. Bring interface up
    run_with_sudo(f"ifconfig {interface_name} up")
    time.sleep(1) # Allow time for the mode change to apply and interface to stabilize

    # 5. Verify the mode change
    if check_success_func(interface_name):
        print(f"INFO: Successfully set interface '{interface_name}' for mode '{target_mode_iw}'.")
        return True
    else:
        print(f"ERROR: Failed to verify mode for '{target_mode_iw}' on '{interface_name}' after attempting to set it.")
        return False

def set_monitor_mode(interface_name):
    """Sets the wireless interface to monitor mode."""
    return _set_interface_mode_generic(interface_name, "monitor", "monitor", is_monitor_mode)

def set_managed_mode(interface_name):
    """Sets the wireless interface to managed (station) mode."""
    # Check function for managed mode is "not is_monitor_mode" or a more specific check if available
    return _set_interface_mode_generic(interface_name, "managed", "managed", lambda iface: not is_monitor_mode(iface))


# --- Wi-Fi Network Scanning (using iwlist) ---
def run_scan(interface_name):
    """
    Scans for Wi-Fi networks using 'iwlist'.
    It's generally better if the interface is in managed mode for 'iwlist scanning'.
    The calling service (network_service.py) should handle mode switching.
    """
    print(f"INFO (utils.run_scan): Scanning for networks on '{interface_name}' using iwlist.")

    # Ensure interface is UP for iwlist scanning
    run_with_sudo(f"ifconfig {interface_name} up")
    time.sleep(1) # Give it a moment

    cmd_iwlist = f"iwlist {interface_name} scanning"
    success, output, error = run_with_sudo(cmd_iwlist)

    if not success:
        print(f"ERROR (utils.run_scan): 'iwlist {interface_name} scanning' failed. Error: {error}")
        if "Network is down" in error or "Device or resource busy" in error:
            print(f"INFO (utils.run_scan): Attempting to bring up '{interface_name}' and retry scan...")
            run_with_sudo(f"ifconfig {interface_name} up") # Try again to ensure it's up
            time.sleep(2)
            success, output, error = run_with_sudo(cmd_iwlist) # Retry
            if not success:
                print(f"ERROR (utils.run_scan): Retry scan also failed. Error: {error}")
                return [] # Return empty list on failure
        else:
            return [] # Return empty list on other failures

    available_aps = []
    current_ap_data = {}
    
    # Parsing logic for iwlist output
    # This needs to be robust to variations in iwlist output.
    for line in output.splitlines():
        line = line.strip()

        if line.startswith("Cell"):
            if current_ap_data.get("BSSID"): # If there's data for a previous cell, save it
                available_aps.append(current_ap_data)
            current_ap_data = {} # Reset for the new cell
            bssid_match = re.search(r"Address: ([\dA-Fa-f:]{17})", line)
            if bssid_match:
                current_ap_data["BSSID"] = bssid_match.group(1)
        
        elif "ESSID:" in line:
            essid_match = re.search(r'ESSID:"([^"]*)"', line)
            if essid_match:
                current_ap_data["ESSID"] = essid_match.group(1) if essid_match.group(1) else "<hidden>"
        
        elif "Channel:" in line and not line.startswith("Frequency:"): # Avoids conflict with Frequency line
            channel_match = re.search(r"Channel:(\d+)", line)
            if channel_match:
                current_ap_data["Channel"] = channel_match.group(1)
        
        elif line.startswith("Frequency:"):
            freq_match = re.search(r"Frequency:([\d.]+ GHz)", line)
            if freq_match:
                current_ap_data["Frequency"] = freq_match.group(1)
            # Often, the channel is also on the Frequency line
            if "Channel" not in current_ap_data: # Only if not already parsed
                channel_freq_match = re.search(r"\(Channel\s*(\d+)\)", line)
                if channel_freq_match:
                    current_ap_data["Channel"] = channel_freq_match.group(1)

        elif "Encryption key:" in line:
            enc_key_status = line.split(":")[1].strip()
            current_ap_data["Encryption"] = enc_key_status # e.g., "on" or "off"
            # More detailed encryption parsing (WPA, WPA2, WEP) often requires looking at IE lines

        elif "Signal level=" in line:
            signal_dbm_match = re.search(r"Signal level=(-?\d+ dBm)", line)
            if signal_dbm_match:
                current_ap_data["Signal"] = signal_dbm_match.group(1)
            else: # Fallback for "X/Y" format
                signal_xy_match = re.search(r"Signal level=(\d+/\d+)", line)
                if signal_xy_match:
                    current_ap_data["Signal"] = signal_xy_match.group(1)
        
        elif "Quality=" in line and "Signal level=" not in current_ap_data.get("Signal", ""):
            # Sometimes signal is only on quality line
            signal_qual_match = re.search(r"Signal level=(-?\d+ dBm)", line)
            if signal_qual_match:
                current_ap_data["Signal"] = signal_qual_match.group(1)


    if current_ap_data.get("BSSID"): # Add the last parsed cell
        available_aps.append(current_ap_data)

    print(f"INFO (utils.run_scan): Scan on '{interface_name}' found {len(available_aps)} APs.")
    return available_aps


# --- Probe Request Sniffing (using tshark) ---
def sniff_probe_requests(interface_name, duration_seconds):
    """
    Sniffs for probe requests on the specified interface for a given duration using tshark.
    Manages interface mode (sets to monitor, then resets to managed).
    Args:
        interface_name (str): The wireless interface to use.
        duration_seconds (int): How long to sniff for probe requests.
    Returns:
        list: A list of unique SSIDs found in probe requests.
    """
    print(f"INFO (utils.sniff_probe_requests): Starting probe request sniffing on '{interface_name}' for {duration_seconds}s.")

    original_mode_is_monitor = is_monitor_mode(interface_name)
    if not original_mode_is_monitor:
        if not set_monitor_mode(interface_name):
            print(f"ERROR (utils.sniff_probe_requests): Failed to set '{interface_name}' to monitor mode.")
            return [] # Cannot sniff probes without monitor mode

    # Command for tshark to capture probe requests and extract SSIDs.
    # -I: Capture in monitor mode (important for tshark on some systems).
    # -i: Specify the interface.
    # -a duration: Stop capturing after 'duration_seconds'.
    # -Y wlan.fc.type_subtype==0x04: Wireshark/tshark display filter for probe request frames.
    # -T fields -e wlan.ssid: Output only the value of the wlan.ssid field.
    tshark_command_str = (
        f"tshark -I -i {interface_name} "
        f"-a duration:{duration_seconds} "
        f"-Y \"wlan.fc.type_subtype == 0x04 && wlan.ssid != \\\"\\\"\" " # Ensure SSID is not empty
        f"-T fields -e wlan.ssid"
    )
    # Note: run_with_sudo will handle prepending 'sudo' if needed.

    ssids_found = set()
    try:
        print(f"DEBUG (utils.sniff_probe_requests): Executing tshark: {tshark_command_str}")
        # Increased timeout for tshark process itself, slightly more than capture duration
        success, stdout, stderr = run_with_sudo(tshark_command_str, timeout=duration_seconds + 15)

        if not success:
            print(f"ERROR (utils.sniff_probe_requests): tshark command failed. STDERR: {stderr}")
            # If tshark mentions "Can't get list of interfaces", it might be a permission or tshark setup issue.
            # If it mentions "capture filter [...] isn't valid", the filter syntax might be wrong for the tshark version.
            return [] # Return empty list on tshark error

        if stdout:
            for line in stdout.splitlines():
                ssid = line.strip()
                if ssid: # Filter out any empty lines that might result
                    ssids_found.add(ssid)
        print(f"INFO (utils.sniff_probe_requests): Found {len(ssids_found)} unique SSIDs from probe requests.")

    except Exception as e:
        print(f"ERROR (utils.sniff_probe_requests): An unexpected error occurred during probe sniffing: {e}")
    finally:
        # Always attempt to restore the interface to its original mode or managed mode.
        print(f"INFO (utils.sniff_probe_requests): Attempting to restore '{interface_name}' mode after sniffing.")
        if original_mode_is_monitor:
            if not set_monitor_mode(interface_name): # Restore to monitor if it was originally
                 print(f"Warning: Failed to restore '{interface_name}' to MONITOR mode.")
        else:
            if not set_managed_mode(interface_name): # Otherwise, set to managed
                 print(f"Warning: Failed to restore '{interface_name}' to MANAGED mode.")
                 
    return sorted(list(ssids_found))


# --- Example of Main Execution (for testing this utility script directly) ---
if __name__ == "__main__":
    print("Testing network_utils.py...")
    test_interface = "wlan0" # Change this to your test interface

    if os.geteuid() != 0:
        print("This test script needs to be run with sudo to manage interface modes.")
        sys.exit(1)

    print(f"\n--- Testing run_with_sudo ---")
    s, o, e = run_with_sudo("echo Hello from sudo")
    print(f"Success: {s}, Output: '{o}', Error: '{e}'")
    s_fail, o_fail, e_fail = run_with_sudo("nonexistentcommand")
    print(f"Failure Test - Success: {s_fail}, Output: '{o_fail}', Error: '{e_fail}'")


    print(f"\n--- Testing Interface Mode Management for '{test_interface}' ---")
    print(f"Initially, is '{test_interface}' in monitor mode? {is_monitor_mode(test_interface)}")
    
    if set_monitor_mode(test_interface):
        print(f"After set_monitor_mode, is '{test_interface}' in monitor mode? {is_monitor_mode(test_interface)}")
        if set_managed_mode(test_interface):
            print(f"After set_managed_mode, is '{test_interface}' in monitor mode? {is_monitor_mode(test_interface)}")
        else:
            print(f"Failed to set '{test_interface}' back to managed mode.")
    else:
        print(f"Failed to set '{test_interface}' to monitor mode for testing.")

    print(f"\n--- Testing run_scan (iwlist) for '{test_interface}' ---")
    # Ensure managed mode for iwlist scan
    if not is_monitor_mode(test_interface) or set_managed_mode(test_interface):
        aps = run_scan(test_interface)
        if aps:
            print(f"Found {len(aps)} access points:")
            for ap in aps[:3]: # Print first 3
                print(f"  {ap.get('ESSID', '<No ESSID>')} ({ap.get('BSSID', 'N/A')}) - Ch: {ap.get('Channel', 'N/A')}, Signal: {ap.get('Signal', 'N/A')}")
        else:
            print("No APs found by run_scan.")
    else:
        print(f"Could not ensure managed mode for {test_interface} to test run_scan.")


    print(f"\n--- Testing sniff_probe_requests for '{test_interface}' (will take ~10s) ---")
    # This will set to monitor and then back to managed
    probed_ssids = sniff_probe_requests(test_interface, 10) # Sniff for 10 seconds
    if probed_ssids:
        print(f"Found {len(probed_ssids)} probed SSIDs: {probed_ssids[:5]}") # Print first 5
    else:
        print("No probed SSIDs found.")

    print("\n--- Ensuring interface is back in managed mode ---")
    set_managed_mode(test_interface)
    print(f"Final check: is '{test_interface}' in monitor mode? {is_monitor_mode(test_interface)}")
    print("\nnetwork_utils.py testing complete.")
