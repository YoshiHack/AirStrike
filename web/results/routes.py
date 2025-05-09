from flask import Blueprint, jsonify, request, render_template, redirect, url_for
import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from .helpers import get_attack_status, get_attack_log, get_captured_handshakes
from web.shared import config

results_bp = Blueprint('results', __name__)
@results_bp.route('/results')
def show_results():
    # Check if sudo is configured before rendering the page
    if not config.get('sudo_configured', False):
        # Redirect directly to sudo auth page
        return redirect(url_for('settings.sudo_auth', next=url_for('results.show_results')))
    
    # If sudo is configured, render the results page
    return render_template('results.html')

@results_bp.route('/attack_status')
def attack_status():
    # Check if sudo is configured
    if not config.get('sudo_configured', False):
        return jsonify({
            'success': False, 
            'error': 'sudo_auth_required',
            'redirect': url_for('settings.sudo_auth', next=request.referrer or url_for('results.show_results'))
        }), 401
    
    return jsonify(get_attack_status())

@results_bp.route('/attack_log')
def attack_log():
    # Check if sudo is configured
    if not config.get('sudo_configured', False):
        return jsonify({
            'success': False, 
            'error': 'sudo_auth_required',
            'redirect': url_for('settings.sudo_auth', next=request.referrer or url_for('results.show_results'))
        }), 401
    
    return jsonify({'log': get_attack_log()})

@results_bp.route('/captured_handshakes')
def captured_handshakes():
    # Check if sudo is configured
    if not config.get('sudo_configured', False):
        return jsonify({
            'success': False, 
            'error': 'sudo_auth_required',
            'redirect': url_for('settings.sudo_auth', next=request.referrer or url_for('results.show_results'))
        }), 401
    
    return jsonify({'handshakes': get_captured_handshakes()})