from flask import Blueprint, jsonify, request, render_template
import threading
import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import shared variables and helpers
from web.shared import *
from web.attacks.helpers import *

attacks_bp = Blueprint('attacks', __name__)

@attacks_bp.route('/attack')
def show_attack():
    return render_template('attack.html')
@attacks_bp.route('/start_attack', methods=['POST'])
def start_attack():
    global attack_state
    
    # Check if an attack is already running
    if attack_state['running']:
        return jsonify({'success': False, 'error': 'An attack is already running'})
    
    data = request.json
    if not data or 'network' not in data or 'attack_type' not in data:
        return jsonify({'success': False, 'error': 'Missing required parameters'})
    
    # Get attack parameters
    network = data['network']
    attack_type = data['attack_type']
    attack_config = data.get('config', {})
    
    # Initialize attack state
    attack_state['running'] = True
    attack_state['attack_type'] = attack_type
    attack_state['target_network'] = network
    attack_state['progress'] = 0
    attack_state['log'] = []
    attack_state['stop_event'] = threading.Event()
    attack_state['threads'] = []
    
    # Log the start of the attack
    log_message(f"Starting {attack_type} attack on {network['essid']} ({network['bssid']})")
    
    try:
        # Launch the appropriate attack
        if attack_type == 'deauth':
            launch_deauth_attack(network, attack_config)
        elif attack_type == 'handshake':
            launch_handshake_attack(network, attack_config)
        elif attack_type == 'evil_twin':
            launch_evil_twin_attack(network, attack_config)
        else:
            attack_state['running'] = False
            return jsonify({'success': False, 'error': f'Unknown attack type: {attack_type}'})
        
        # Update stats
        stats['attacks_count'] += 1
        
        return jsonify({'success': True})
    except Exception as e:
        attack_state['running'] = False
        attacks_bp.logger.error(f"Error starting attack: {e}")
        return jsonify({'success': False, 'error': str(e)})

@attacks_bp.route('/stop_attack', methods=['POST'])
def stop_attack():
    global attack_state
    
    if not attack_state['running']:
        return jsonify({'success': False, 'error': 'No attack is running'})
    
    try:
        # Signal threads to stop
        if attack_state['stop_event']:
            attack_state['stop_event'].set()
        
        # Wait for threads to finish
        for thread in attack_state['threads']:
            thread.join(timeout=2)
        
        # Reset interface to managed mode
        set_managed_mode(config['interface'])
        
        # Update attack state
        attack_state['running'] = False
        log_message("Attack stopped")
        
        return jsonify({'success': True})
    except Exception as e:
        attacks_bp.logger.error(f"Error stopping attack: {e}")
        return jsonify({'success': False, 'error': str(e)})

@attacks_bp.route('/attack_status')
def attack_status():
    return jsonify({
        'running': attack_state['running'],
        'attack_type': attack_state['attack_type'],
        'target_network': attack_state['target_network'],
        'progress': attack_state['progress']
    })

@attacks_bp.route('/attack_log')
def attack_log():
    return jsonify({
        'log': attack_state['log']
    })
    
    
