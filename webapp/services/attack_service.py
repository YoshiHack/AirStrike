# AirStrike/webapp/services/attack_service.py
import os
import sys
import uuid
import time
import threading
from flask import current_app # For logging and accessing app.config

# --- Path Setup for core_attacks and utils ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    # Import your actual attack worker functions from core_attacks
    # These will need to be adapted to be callable and to report logs/status
    from core_attacks.deauth_attack import deauth_attack_worker # Example name
    from core_attacks.capture_attack import capture_handshake_worker # Example name
    from core_attacks.evil_twin import evil_twin_worker # Example name
    from core_attacks.karma_attack import karma_attack_worker # Example name
    # Add other imports for DOS, Beacon Flood, etc. as you create/adapt them

    from utils.network_utils import set_managed_mode, set_monitor_mode, is_monitor_mode
    # Import the main_routes stats update functions (or use a proper stats service)
    from webapp.main_routes import increment_attacks_launched_stat, update_handshakes_captured_stat

except ImportError as e:
    print(f"ERROR (attack_service.py): Failed to import modules: {e}. Placeholders will be used.")
    # Define placeholder functions if imports fail, so the app can at least start.
    def placeholder_attack_worker(attack_id, params, log_callback, status_callback, stop_event):
        log_callback(attack_id, "Placeholder attack worker started.")
        for i in range(5):
            if stop_event.is_set():
                log_callback(attack_id, "Placeholder attack stopped by event.")
                status_callback(attack_id, "stopped", 100)
                return
            time.sleep(1)
            log_callback(attack_id, f"Placeholder attack progress {i+1}/5.")
            status_callback(attack_id, "running", (i+1)*20)
        log_callback(attack_id, "Placeholder attack completed.")
        status_callback(attack_id, "completed", 100)

    deauth_attack_worker = placeholder_attack_worker
    capture_handshake_worker = placeholder_attack_worker
    evil_twin_worker = placeholder_attack_worker
    karma_attack_worker = placeholder_attack_worker
    # Define other placeholders...

    def set_managed_mode(iface): print(f"Placeholder: set_managed_mode({iface})"); return True
    def increment_attacks_launched_stat(): print("Placeholder: increment_attacks_launched_stat()")
    def update_handshakes_captured_stat(c): print(f"Placeholder: update_handshakes_captured_stat({c})")


# --- In-memory storage for attack status and logs ---
# This is a simple approach. For a more robust system, consider a database or a more
# sophisticated in-memory store like Redis, especially if you expect many concurrent attacks
# or need persistence across server restarts (which this doesn't provide).
_active_attacks = {} # Stores attack_id: {thread, stop_event, status, progress, logs, params}

def _log_message_for_attack(attack_id, message):
    """Appends a timestamped message to the specific attack's log."""
    if attack_id in _active_attacks:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        # Limit the number of log lines stored in memory
        max_lines = current_app.config.get('MAX_LOG_LINES_MEMORY', 200)
        _active_attacks[attack_id]['logs'].append(log_entry)
        if len(_active_attacks[attack_id]['logs']) > max_lines:
            _active_attacks[attack_id]['logs'] = _active_attacks[attack_id]['logs'][-max_lines:]
        # current_app.logger.debug(f"AttackLog ({attack_id}): {message}") # Optional: also log to main app log
    else:
        current_app.logger.warning(f"Attempted to log for non-existent attack_id: {attack_id}")

def _update_attack_status(attack_id, status, progress=None):
    """Updates the status and progress of a specific attack."""
    if attack_id in _active_attacks:
        _active_attacks[attack_id]['status'] = status
        if progress is not None:
            _active_attacks[attack_id]['progress'] = min(max(0, progress), 100) # Clamp progress 0-100
        current_app.logger.info(f"AttackStatus ({attack_id}): Status='{status}', Progress={_active_attacks[attack_id]['progress']}%")
    else:
        current_app.logger.warning(f"Attempted to update status for non-existent attack_id: {attack_id}")


def start_attack_service(network_params, attack_type, attack_config_params):
    """
    Starts a new attack based on the provided parameters.
    Manages the attack in a separate thread.
    Returns: (attack_id, initial_message, error_message)
    """
    current_app.logger.info(f"Service: Attempting to start '{attack_type}' attack. Target: {network_params.get('essid', 'N/A')}, Config: {attack_config_params}")

    # Check for existing running attack (simple check, could be more sophisticated)
    # This example allows multiple attacks if your hardware/scripts can handle it.
    # If you want to limit to one active attack, you'd check _active_attacks here.

    attack_id = str(uuid.uuid4()) # Generate a unique ID for this attack instance
    stop_event = threading.Event()

    # Prepare parameters for the specific attack worker
    # The worker functions (e.g., deauth_attack_worker) need to be designed to accept:
    # attack_id, network_params, attack_config_params, log_callback, status_callback, stop_event
    # and the app_config from current_app.config
    
    shared_attack_params = {
        "attack_id": attack_id,
        "network_params": network_params,
        "attack_config_params": attack_config_params,
        "log_callback": _log_message_for_attack,
        "status_callback": _update_attack_status,
        "stop_event": stop_event,
        "app_config": dict(current_app.config) # Pass a copy of app config
    }

    target_worker = None
    if attack_type == 'deauth':
        target_worker = deauth_attack_worker
    elif attack_type == 'handshake':
        target_worker = capture_handshake_worker
    elif attack_type == 'evil_twin':
        target_worker = evil_twin_worker
    elif attack_type == 'karma':
        target_worker = karma_attack_worker
    # Add elif for other attack types (dos, beacon_flood, etc.)
    # elif attack_type == 'dos':
    #     target_worker = dos_attack_worker # You'll need to create/adapt this
    else:
        err_msg = f"Unknown attack type: '{attack_type}'."
        current_app.logger.error(err_msg)
        return None, None, err_msg

    thread = threading.Thread(target=target_worker, kwargs=shared_attack_params, daemon=True)
    
    _active_attacks[attack_id] = {
        'thread': thread,
        'stop_event': stop_event,
        'status': 'starting',
        'progress': 0,
        'logs': [],
        'params': { # Store original params for reference
            'network': network_params,
            'type': attack_type,
            'config': attack_config_params
        },
        'start_time': time.time()
    }

    try:
        thread.start()
        _log_message_for_attack(attack_id, f"'{attack_type}' attack initiated successfully.")
        _update_attack_status(attack_id, "running", 5) # Initial progress
        increment_attacks_launched_stat() # Update general app stats
        return attack_id, f"Attack '{attack_type}' (ID: {attack_id}) started.", None
    except Exception as e:
        current_app.logger.error(f"Failed to start attack thread for '{attack_type}' (ID: {attack_id}): {e}", exc_info=True)
        _log_message_for_attack(attack_id, f"Error: Could not start attack thread: {e}")
        _update_attack_status(attack_id, "failed", 0)
        # Clean up if thread failed to start
        if attack_id in _active_attacks:
            del _active_attacks[attack_id]
        return None, None, f"Failed to start attack thread: {e}"


def stop_attack_service(attack_id):
    """
    Signals a running attack to stop.
    """
    current_app.logger.info(f"Service: Attempting to stop attack with ID: {attack_id}")
    attack_info = _active_attacks.get(attack_id)

    if not attack_info:
        return False, "Attack ID not found or already stopped."

    if attack_info['status'] in ['stopping', 'completed', 'failed', 'stopped']:
        return True, f"Attack {attack_id} is already {attack_info['status']}."

    _log_message_for_attack(attack_id, "Stop signal received. Attempting to halt attack...")
    _update_attack_status(attack_id, "stopping", attack_info.get('progress',0)) # Keep current progress
    attack_info['stop_event'].set()

    # Give the thread some time to stop. The thread itself should handle cleanup.
    # The frontend will continue polling for the final 'stopped' or 'completed' status.
    # We don't join the thread here to avoid blocking the web request.
    # The attack worker itself should call status_callback with 'stopped' or 'completed'.
    
    # Optional: Start a separate cleanup monitor for this attack_id if thread doesn't stop
    # For now, rely on the worker to set its final status.

    return True, f"Stop signal sent to attack {attack_id}. Monitor status for completion."

def get_attack_status_service(attack_id):
    """
    Retrieves the current status and logs for a given attack_id.
    """
    attack_info = _active_attacks.get(attack_id)
    if not attack_info:
        return None # Or {'status': 'not_found', 'logs': [], 'progress': 0}

    # If thread is no longer alive and status hasn't been finalized, mark as completed/failed
    if not attack_info['thread'].is_alive() and \
       attack_info['status'] not in ['completed', 'failed', 'stopped']:
        current_app.logger.warning(f"Attack thread for {attack_id} is dead but status is '{attack_info['status']}'. Marking as 'unknown_completion'.")
        _update_attack_status(attack_id, "unknown_completion", attack_info.get('progress', 100))
        _log_message_for_attack(attack_id, "Attack thread ended unexpectedly.")


    return {
        'attack_id': attack_id,
        'status': attack_info['status'],
        'progress': attack_info['progress'],
        'logs': list(attack_info['logs']), # Return a copy
        'params': attack_info['params'],
        'start_time': attack_info['start_time']
    }

def get_all_active_attacks_service():
    """
    Returns a summary of all currently active or recently completed attacks.
    """
    summary = []
    # Iterate over a copy of keys in case of modification during iteration (less likely here)
    for attack_id, info in list(_active_attacks.items()):
        # Clean up very old, completed/failed attacks from memory after a while
        # Example: remove if older than 1 hour and not running
        if info['status'] in ['completed', 'failed', 'stopped'] and (time.time() - info.get('start_time', 0)) > 3600:
            current_app.logger.info(f"Cleaning up old attack entry: {attack_id}")
            try:
                del _active_attacks[attack_id]
            except KeyError:
                pass # Already removed by another request
            continue

        summary.append({
            'attack_id': attack_id,
            'type': info['params']['type'],
            'target': info['params']['network'].get('essid', 'N/A'),
            'status': info['status'],
            'progress': info['progress'],
            'start_time': info['start_time']
        })
    return summary

# --- Cleanup for old attacks (can be run periodically if needed) ---
# This is a simple in-memory cleanup.
def cleanup_old_attacks():
    # This function could be called by a background scheduler if you had one.
    # For now, it's integrated into get_all_active_attacks_service.
    pass

