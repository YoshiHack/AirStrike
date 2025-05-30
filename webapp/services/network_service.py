# AirStrike/webapp/services/network_service.py
import os
import sys
import re
import subprocess # For direct calls if run_with_sudo is not used for certain non-sudo commands
from flask import current_app # To access app.config and app.logger

# --- Path Setup for utils ---
# Ensures 'utils' package (containing network_utils.py) can be imported.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from utils.network_utils import (
        run_scan as util_run_scan_iwlist, # Specifically for iwlist scan
        is_monitor_mode as util_is_monitor_mode,
        set_managed_mode as util_set_managed_mode,
        set_monitor_mode as util_set_monitor_mode,
        run_with_sudo, # Assuming this is your primary sudo command runner
        sniff_probe_requests as util_sniff_probe_requests # For probe sniffing
    )
except ImportError as e:
    # Fallback definitions if utils cannot be imported (should not happen in a correct setup)
    current_app.logger.critical(f"CRITICAL: Failed to import from utils.network_utils: {e}. Using placeholders.")
    def run_with_sudo(cmd_str): return False, "", f"Error: run_with_sudo placeholder due to import error: {e}"
    util_run_scan_iwlist = lambda iface: ([], f"Error: util_run_scan_iwlist placeholder: {e}")
    util_is_monitor_mode = lambda iface: False
    util_set_managed_mode = lambda iface: False
    util_set_monitor_mode = lambda iface: False
    util_sniff_probe_requests = lambda iface, dur: ([], f"Error: util_sniff_probe_requests placeholder: {e}")


# --- Service Functions for Network Operations ---

def check_interface_status_detailed(interface_name):
    """
    Checks and returns detailed status of a given network interface.
    """
    status_info = {
        'name': interface_name,
        'exists': False,
        'is_wireless': False,
        'mode': 'Unknown',
        'status': 'Unknown',
        'mac_address': 'N/A',
        'driver': 'N/A',
    }
    current_app.logger.debug(f"Service: Checking detailed status for interface '{interface_name}'.")

    try:
        # 1. Check interface existence and state (UP/DOWN) with 'ip link show'
        cmd_ip_link = f"ip link show {interface_name}"
        success, output_ip, err_ip = run_with_sudo(cmd_ip_link)
        if success and output_ip:
            status_info['exists'] = True
            status_info['status'] = "UP" if "UP" in output_ip else ("DOWN" if "DOWN" in output_ip else "Unknown")
            mac_match = re.search(r"link/ether\s+([0-9a-fA-F:]{17})", output_ip)
            if mac_match: status_info['mac_address'] = mac_match.group(1)
        else:
            current_app.logger.warning(f"Failed to get 'ip link show' for '{interface_name}'. Error: {err_ip}")
            return status_info # Interface likely doesn't exist

        # 2. Check wireless properties with 'iwconfig'
        cmd_iwconfig = f"iwconfig {interface_name}"
        success_iw, output_iw, err_iw = run_with_sudo(cmd_iwconfig)
        if success_iw and output_iw:
            if "no wireless extensions" not in output_iw.lower():
                status_info['is_wireless'] = True
                mode_match = re.search(r"Mode:(\w+)", output_iw)
                if mode_match: status_info['mode'] = mode_match.group(1)
            else:
                status_info['is_wireless'] = False # Not a wireless interface
        else:
            current_app.logger.info(f"'iwconfig {interface_name}' failed or no wireless extensions. Error: {err_iw}")
            status_info['is_wireless'] = False # Assume not wireless if iwconfig fails or indicates so

        # (Optional) Get driver info with 'ethtool -i <interface>'
        # This requires ethtool to be installed.
        # success_et, output_et, err_et = run_with_sudo(f"ethtool -i {interface_name}")
        # if success_et and output_et:
        #     driver_match = re.search(r"driver:\s*(\S+)", output_et)
        #     if driver_match: status_info['driver'] = driver_match.group(1)

    except Exception as e:
        current_app.logger.error(f"Exception in check_interface_status_detailed for '{interface_name}': {e}", exc_info=True)
    
    current_app.logger.debug(f"Service: Detailed status for '{interface_name}': {status_info}")
    return status_info


def scan_wifi_networks_service(interface_name):
    """
    Scans for Wi-Fi networks using 'iwlist'.
    Temporarily sets interface to managed mode if it's in monitor mode, then restores.
    Returns: (list_of_networks, error_message_or_none)
    """
    current_app.logger.info(f"Service: Starting Wi-Fi scan on interface '{interface_name}' using iwlist.")
    
    original_mode_is_monitor = util_is_monitor_mode(interface_name)
    if original_mode_is_monitor:
        current_app.logger.info(f"Interface '{interface_name}' is in monitor mode. Setting to managed for iwlist scan.")
        if not util_set_managed_mode(interface_name): # This should use run_with_sudo internally
            err_msg = f"Failed to switch '{interface_name}' to managed mode for scanning."
            current_app.logger.error(err_msg)
            return [], err_msg
    
    networks = []
    error_msg = None
    try:
        # util_run_scan_iwlist is your function from utils.network_utils that uses 'iwlist'
        networks = util_run_scan_iwlist(interface_name)
        if not networks and not any(n.get('BSSID') for n in networks): # Check if scan returned anything meaningful
             current_app.logger.info(f"Scan on '{interface_name}' returned no valid APs.")
             # error_msg = "No networks found or scan failed to retrieve details." # Optional: treat empty as error
    except Exception as e:
        current_app.logger.error(f"Exception during Wi-Fi scan service for '{interface_name}': {e}", exc_info=True)
        error_msg = f"Scan service error: {str(e)}"
    finally:
        if original_mode_is_monitor:
            current_app.logger.info(f"Restoring '{interface_name}' to monitor mode after scan.")
            if not util_set_monitor_mode(interface_name): # This should use run_with_sudo internally
                warn_msg = f"Warning: Failed to restore '{interface_name}' to monitor mode post-scan."
                current_app.logger.warning(warn_msg)
                error_msg = f"{error_msg or ''} {warn_msg}".strip()
    
    if error_msg:
         current_app.logger.error(f"Wi-Fi scan service for '{interface_name}' finished with error: {error_msg}")
    else:
        current_app.logger.info(f"Wi-Fi scan service for '{interface_name}' found {len(networks)} potential APs.")

    # Update stats (example, needs proper implementation via main_routes or a stats service)
    from webapp.main_routes import update_networks_scanned_stat
    update_networks_scanned_stat(len(networks))

    return networks, error_msg


def get_available_interfaces_service():
    """
    Retrieves a list of available wireless network interfaces.
    Tries 'iw dev' first, then falls back to other methods or defaults.
    """
    current_app.logger.debug("Service: Fetching available wireless interfaces.")
    interfaces = []
    try:
        # Try 'iw dev' for modern systems
        success, output, error = run_with_sudo("iw dev")
        if success and output:
            for line in output.splitlines():
                if line.strip().startswith("Interface"):
                    parts = line.split()
                    if len(parts) > 1:
                        interfaces.append(parts[1])
            if interfaces:
                current_app.logger.info(f"Service: Detected wireless interfaces via 'iw dev': {interfaces}")
                return interfaces
            else:
                current_app.logger.warning("Service: 'iw dev' found no interfaces.")
        else:
            current_app.logger.warning(f"Service: 'iw dev' command failed or no output. Error: {error}")

        # Fallback: Try parsing 'ip link' and checking for 'wlan' or 'wifi' in name
        # This is less reliable for determining wireless capability but a common heuristic.
        current_app.logger.info("Service: Falling back to 'ip link' for interface detection.")
        success_ip, output_ip, error_ip = run_with_sudo("ip -o link show")
        if success_ip and output_ip:
            for line in output_ip.splitlines():
                parts = line.split(':')
                if len(parts) > 1:
                    ifname = parts[1].strip().split('@')[0] # Get name before @ for virtual ifs
                    if ifname.startswith(('wlan', 'wifi', 'ath', 'ra')): # Common wireless prefixes
                        interfaces.append(ifname)
            if interfaces:
                # Remove duplicates that might arise from different detection methods
                interfaces = sorted(list(set(interfaces)))
                current_app.logger.info(f"Service: Detected interfaces via 'ip link': {interfaces}")
                return interfaces
            else:
                current_app.logger.warning("Service: 'ip link' found no likely wireless interfaces.")
        else:
            current_app.logger.warning(f"Service: 'ip link' command failed. Error: {error_ip}")

    except Exception as e:
        current_app.logger.error(f"Service: Exception while getting available interfaces: {e}", exc_info=True)
    
    # Final fallback to default interface from config
    default_iface = current_app.config.get('DEFAULT_INTERFACE', 'wlan0')
    current_app.logger.warning(f"Service: No interfaces detected, falling back to default: {default_iface}")
    return [default_iface]

def set_interface_service(interface_name):
    """
    Sets the application's default interface in the configuration.
    Note: This updates the runtime config, not persisted unless you save config to a file.
    """
    if interface_name:
        # Basic validation: check if it's in the list of available interfaces (optional but good)
        # available_interfaces = get_available_interfaces_service()
        # if interface_name not in available_interfaces:
        #     current_app.logger.warning(f"Attempt to set unknown interface: {interface_name}")
        #     return False, f"Interface {interface_name} not found or not available."

        current_app.config['DEFAULT_INTERFACE'] = interface_name
        current_app.logger.info(f"Service: Default interface set to '{interface_name}' in runtime config.")
        # Example: Update stats if you track current interface there
        from webapp.main_routes import _app_stats # Be cautious with direct global/module var access
        _app_stats['current_interface'] = interface_name
        return True, f"Interface set to {interface_name}"
    return False, "No interface name provided."

def sniff_probe_requests_service(interface_name, duration):
    """
    Service function to sniff probe requests.
    Uses the utility function from utils.network_utils.
    """
    current_app.logger.info(f"Service: Starting probe request sniffing on '{interface_name}' for {duration}s.")
    try:
        # util_sniff_probe_requests should handle monitor mode internally
        ssids_found = util_sniff_probe_requests(interface_name, duration)
        current_app.logger.info(f"Service: Probe sniffing on '{interface_name}' yielded {len(ssids_found)} SSIDs.")
        return ssids_found, None
    except Exception as e:
        current_app.logger.error(f"Service: Error during probe request sniffing for '{interface_name}': {e}", exc_info=True)
        return [], f"Probe sniffing service error: {str(e)}"

