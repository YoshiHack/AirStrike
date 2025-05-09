from flask import Blueprint, jsonify, request, render_template
import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from web.shared import *
from .helpers import scan_wifi_networks

scan_bp = Blueprint('scan', __name__)
@scan_bp.route('/scan')
def show_scan():
    return render_template('scan.html')

@scan_bp.route('/scan_wifi')
def scan_wifi():
    networks, error = scan_wifi_networks()
    if error:
        scan_bp.logger.error(f"Error scanning networks: {error}")
        return jsonify([]), 500
    return jsonify(networks)