# AirStrike/webapp/attack_routes.py
from flask import Blueprint, jsonify, request, render_template, current_app
# Ensure this import path is correct based on your services directory structure
from .services import attack_service # Uses the attack_service.py

# Define the Blueprint for attack-related routes
# 'attack' is the name of the blueprint, used internally by Flask (e.g., for url_for)
# The url_prefix='/attack' will be set when registering this blueprint in webapp/__init__.py
attack_bp = Blueprint('attack', __name__, template_folder='templates')


@attack_bp.route('/')  # This will be mapped to /attack/
def show_attack_configuration_page():
    """
    Renders the main attack configuration page (attack.html).
    """
    current_app.logger.info("Route: GET /attack/ - Rendering attack configuration page.")
    # You might want to pass data to the template, e.g., available interfaces or networks.
    # For now, it just renders the page. JavaScript on the page will handle fetching data.
    return render_template('attack.html')


@attack_bp.route('/start', methods=['POST'])  # Mapped to /attack/start
def start_attack_endpoint():
    """
    API endpoint to start a new attack.
    Expects JSON payload with:
    {
        "network": {"bssid": "...", "essid": "...", "channel": "..."}, // Network details
        "attack_type": "deauth" | "handshake" | "evil_twin" | "karma" | ..., // Type of attack
        "config": { ... attack-specific parameters ... } // Configuration for the chosen attack
    }
    """
    current_app.logger.info("Route: POST /attack/start - Request received to start an attack.")
    data = request.get_json()

    if not data:
        current_app.logger.warning("Bad Request: No JSON data received for /attack/start.")
        return jsonify(success=False, error="Invalid request: No JSON data provided."), 400

    # Extract parameters from the JSON payload
    network_params = data.get('network')
    attack_type = data.get('attack_type')
    attack_config_params = data.get('config', {})  # Default to an empty dict if 'config' is not provided

    # --- Basic Validation of Incoming Data ---
    if not network_params or not isinstance(network_params, dict):
        current_app.logger.warning(f"Bad Request: Missing or invalid 'network' parameters: {network_params}")
        return jsonify(success=False, error="Invalid request: 'network' parameters object is required."), 400
    
    # BSSID and Channel are usually essential for targeting. ESSID can sometimes be optional (e.g. hidden networks).
    if not network_params.get('bssid') or network_params.get('channel') is None:
        current_app.logger.warning(f"Bad Request: 'bssid' and 'channel' within 'network' are required. Got: {network_params}")
        return jsonify(success=False, error="Invalid request: 'network.bssid' and 'network.channel' are required."), 400

    if not attack_type or not isinstance(attack_type, str):
        current_app.logger.warning(f"Bad Request: Missing or invalid 'attack_type'. Got: {attack_type}")
        return jsonify(success=False, error="Invalid request: 'attack_type' (string) is required."), 400

    current_app.logger.info(f"Processing start attack request: Type='{attack_type}', Target='{network_params.get('essid', network_params['bssid'])}', Config='{attack_config_params}'")

    # Call the service layer to handle the attack logic
    attack_id, message, error = attack_service.start_attack_service(
        network_params,
        attack_type,
        attack_config_params
    )

    if error or not attack_id:
        current_app.logger.error(f"Failed to start attack '{attack_type}': {error}")
        # Return 500 for server-side issues, 400 for bad input if error indicates that
        return jsonify(success=False, error=error or "Failed to initiate attack due to an internal error."), 500

    current_app.logger.info(f"Attack '{attack_type}' (ID: {attack_id}) successfully initiated. Message: {message}")
    # 202 Accepted: The request has been accepted for processing, but the processing has not been completed.
    return jsonify(success=True, message=message, attack_id=attack_id), 202


@attack_bp.route('/stop/<attack_id>', methods=['POST'])  # Mapped to /attack/stop/<attack_id>
def stop_attack_endpoint(attack_id):
    """
    API endpoint to signal a running attack (specified by attack_id) to stop.
    """
    current_app.logger.info(f"Route: POST /attack/stop/{attack_id} - Request to stop attack.")
    
    if not attack_id: # Should be caught by Flask routing if <attack_id> is part of URL rule
        current_app.logger.warning("Bad Request: No attack_id provided for stopping attack.")
        return jsonify(success=False, error="Attack ID is required."), 400

    success, message = attack_service.stop_attack_service(attack_id)

    if not success:
        current_app.logger.warning(f"Failed to issue stop for attack '{attack_id}': {message}")
        # 404 if attack_id not found, 500 if other internal error stopping.
        status_code = 404 if "not found" in message.lower() else 500
        return jsonify(success=False, error=message), status_code

    current_app.logger.info(f"Stop signal successfully sent for attack '{attack_id}'. Client should poll status. Message: {message}")
    return jsonify(success=True, message=message) # Client will poll /status/<attack_id> for final state


@attack_bp.route('/status/<attack_id>', methods=['GET'])  # Mapped to /attack/status/<attack_id>
def get_attack_status_endpoint(attack_id):
    """
    API endpoint for the frontend to poll for the status and logs of a specific ongoing attack.
    """
    # This endpoint can be called frequently, so keep logging to DEBUG or less verbose if needed.
    # current_app.logger.debug(f"Route: GET /attack/status/{attack_id} - Polling status.")
    
    if not attack_id:
        return jsonify(success=False, error="Attack ID is required."), 400

    status_data = attack_service.get_attack_status_service(attack_id)

    if not status_data:
        # current_app.logger.debug(f"Status poll for unknown or cleaned up attack ID: {attack_id}")
        return jsonify(success=False, error="Attack ID not found or attack has been cleared from memory."), 404
    
    # current_app.logger.debug(f"Returning status for attack '{attack_id}': Status='{status_data.get('status')}', Progress={status_data.get('progress')}%")
    return jsonify(success=True, data=status_data)


@attack_bp.route('/active_list', methods=['GET'])  # Mapped to /attack/active_list
def get_active_attacks_list_endpoint():
    """
    API endpoint to get a summary list of all currently managed attacks (active or recent).
    Useful for an overview page or for the results page to know which attacks to potentially poll.
    """
    current_app.logger.info("Route: GET /attack/active_list - Fetching list of active/recent attacks.")
    attacks_summary = attack_service.get_all_active_attacks_service()
    return jsonify(success=True, attacks=attacks_summary)
