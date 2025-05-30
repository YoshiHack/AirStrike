# AirStrike/webapp/services/diagnostics_service.py
from flask import current_app
import platform
import sys
import os
import shutil # For shutil.which to check if commands exist

# Assuming network_utils contains run_with_sudo and interface detail functions
# Adjust path if your project structure is different or if these are elsewhere
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from utils.network_utils import run_with_sudo
    # If get_interface_details was in your utils, import it.
    # For now, we'll use network_service.check_interface_status_detailed
    from webapp.services.network_service import check_interface_status_detailed
except ImportError as e:
    current_app.logger.error(f"CRITICAL (diagnostics_service): Failed to import utils: {e}")
    def run_with_sudo(cmd_str, timeout=30): return False, "", f"Error: run_with_sudo placeholder due to import error: {e}"
    def check_interface_status_detailed(iface): return {"name": iface, "error": "network_service not loaded"}


def get_system_info_service():
    """
    Gathers basic system information.
    """
    current_app.logger.debug("Service: Gathering system information.")
    info = {
        'python_version': sys.version.split()[0],
        'platform_system': platform.system(),
        'platform_release': platform.release(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'hostname': platform.node(),
        'current_user_euid': os.geteuid() if hasattr(os, 'geteuid') else 'N/A',
        'current_user_uid': os.getuid() if hasattr(os, 'getuid') else 'N/A',
        'is_root': (os.geteuid() == 0) if hasattr(os, 'geteuid') else False,
    }
    
    # Get OS name more reliably if on Linux
    if platform.system() == "Linux":
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        info['os_pretty_name'] = line.split("=")[1].strip().strip('"')
                        break
        except FileNotFoundError:
            info['os_pretty_name'] = "Linux (os-release not found)"
    
    current_app.logger.debug(f"Service: System Info: {info}")
    return info

def get_interface_diagnostics_service(interface_name):
    """
    Gets detailed diagnostics for a specific network interface.
    This reuses the check_interface_status_detailed from network_service.
    """
    current_app.logger.debug(f"Service: Getting diagnostics for interface '{interface_name}'.")
    # This function is already quite detailed.
    return check_interface_status_detailed(interface_name)


def run_diagnostic_command_service(command_str):
    """
    Executes a whitelisted diagnostic command using run_with_sudo.
    Args:
        command_str (str): The command string to execute.
    Returns:
        tuple: (success_bool, output_str, error_str_if_any)
    """
    current_app.logger.info(f"Service: Attempting to run diagnostic command: '{command_str}'")

    # --- Whitelist of allowed commands/prefixes ---
    # This is crucial for security to prevent arbitrary command execution.
    # Make this list as restrictive as possible.
    allowed_command_prefixes = [
        "iwconfig",
        "ifconfig", # Often needs interface name
        "ip addr", "ip link", "ip route", "ip neigh",
        "iw dev", # Often needs interface name and subcommands like 'link', 'scan'
        "iwlist", # Often needs interface name and 'scanning'
        "ethtool -i", # Needs interface name
        "rfkill list",
        "lsmod", # Can be piped with grep, e.g., "lsmod | grep ath"
        "dmesg | tail", # Example of a piped command
        "ping -c 3", # Example with arguments, ensure target is safe (e.g., localhost or gateway)
        "nmcli dev status", "nmcli dev show", # NetworkManager
        "lspci -nnk | grep -i network", # List network controllers
        "lsusb | grep -i wlan", # List USB WLAN adapters
    ]

    is_allowed = False
    # For piped commands, check the first part.
    main_command_part = command_str.split('|')[0].strip()

    for prefix in allowed_command_prefixes:
        if main_command_part.startswith(prefix):
            is_allowed = True
            break
    
    if not is_allowed:
        err_msg = f"Command not allowed for diagnostics: '{command_str}'. Main part: '{main_command_part}'"
        current_app.logger.warning(f"Service: {err_msg}")
        return False, "", err_msg

    # Execute the command using run_with_sudo
    # The run_with_sudo function should handle splitting the command string correctly.
    success, output, error = run_with_sudo(command_str)

    if success:
        current_app.logger.info(f"Service: Diagnostic command '{command_str}' executed successfully.")
    else:
        current_app.logger.warning(f"Service: Diagnostic command '{command_str}' failed. Error: {error}")
    
    return success, output, error

def check_tool_availability_service():
    """
    Checks for the presence of essential command-line tools.
    """
    tools = {
        "aireplay-ng": None, "aircrack-ng": None, "airodump-ng": None,
        "tshark": None, "iwconfig": None, "ifconfig": None, "ip": None,
        "iw": None, "hostapd": None, "dnsmasq": None, "ethtool": None,
        "rfkill": None, "nmcli": None, "ping": None
    }
    current_app.logger.debug("Service: Checking availability of essential tools.")
    for tool_name in tools.keys():
        path = shutil.which(tool_name)
        if path:
            tools[tool_name] = {"status": "Found", "path": path}
        else:
            # Try with sudo prefix for tools that might only be in root's path
            # This is less common for `which` but can happen.
            # More reliably, check common paths like /usr/sbin, /sbin if `which` fails.
            # For simplicity, just using `which` for now.
            tools[tool_name] = {"status": "Not Found", "path": None}
            current_app.logger.warning(f"Tool '{tool_name}' not found in PATH.")
            
    current_app.logger.debug(f"Service: Tool availability check: {tools}")
    return tools

