# airstrike/webapp/attack_routes.py
from flask import Blueprint, jsonify, request, render_template, current_app
from .services import attack_service # Assuming you create this service layer

attacks_bp = Blueprint('attacks', __name__, template_folder='templates')

@attacks_bp.route('/') # Assuming /attack/ is the base for this blueprint
def show_attack_page():
    # Logic to pass necessary data to the attack.html template
    return render_template('attack.html')

@attacks_bp.route('/start', methods=['POST'])
def start_attack_route():
    data = request.json
    network_params = data.get('network')
    attack_type = data.get('attack_type')
    attack_config_params = data.get('config', {})

    if not network_params or not attack_type:
        return jsonify({'success': False, 'error': 'Missing network or attack_type'}), 400

    current_app.logger.info(f"Request to start {attack_type} on {network_params.get('essid')}")

    result = None
    if attack_type == 'deauth':
        result = attack_service.start_deauth_attack(network_params, attack_config_params)
    elif attack_type == 'handshake':
        result = attack_service.start_handshake_attack(network_params, attack_config_params)
    # Add other attack types
    else:
        return jsonify({'success': False, 'error': f'Unknown attack type: {attack_type}'}), 400

    return jsonify({'success': True, 'data': result})

@attacks_bp.route('/status/<attack_id>', methods=['GET'])
def attack_status_route(attack_id):
    status = attack_service.get_attack_status(attack_id)
    logs = attack_service.get_attack_logs(attack_id)
    return jsonify({'success': True, 'status': status, 'logs': logs})

# Add a stop_attack route if necessary