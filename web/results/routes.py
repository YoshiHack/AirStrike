from flask import Blueprint, jsonify, request, render_template
import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from .helpers import get_attack_status, get_attack_log, get_captured_handshakes

results_bp = Blueprint('results', __name__)
@results_bp.route('/results')
def show_results():
    return render_template('results.html')

@results_bp.route('/attack_status')
def attack_status():
    return jsonify(get_attack_status())

@results_bp.route('/attack_log')
def attack_log():
    return jsonify({'log': get_attack_log()})

@results_bp.route('/captured_handshakes')
def captured_handshakes():
    return jsonify({'handshakes': get_captured_handshakes()})