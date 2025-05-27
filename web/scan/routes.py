"""
Routes for network scanning functionality in the AirStrike web interface.
"""

from flask import Blueprint, jsonify, request, render_template, redirect, url_for
import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from web.shared import logger, config, is_sudo_authenticated
from .helpers import scan_wifi_networks, check_interface_status
from utils import network_utils

scan_bp = Blueprint('scan', __name__)

@scan_bp.route('/scan')
def show_scan():
    """Render the network scanning page"""
    # No need to check sudo anymore since we enforce root execution
    return render_template('scan.html')

@scan_bp.route('/scan_wifi')
def scan_wifi():
    """
    Scan for available WiFi networks using the configured interface.
    
    Returns:
        JSON array of networks or empty array with 500 status on error
    """
    # Root execution is enforced at startup, so no need to check here anymore
    
    interface = request.args.get('interface', config['interface'])
    check_only = request.args.get('check_only', 'false').lower() == 'true'
    
    # Check interface status
    interface_status = check_interface_status(interface)
    
    # If only checking interface status, return that
    if check_only:
        return jsonify({
            'success': True,
            'interface_status': interface_status
        })
    
    try:
        networks, error = scan_wifi_networks(interface)
        if error:
            # Since we're running as root, this shouldn't happen, but log it anyway
            if "permission" in error.lower():
                logger.error(f"Permission error despite running as root: {error}")
                return jsonify({
                    'success': False, 
                    'error': error,
                    'interface_status': interface_status
                }), 500
            
            logger.error(f"Error scanning networks: {error}")
            return jsonify({
                'success': False, 
                'error': error,
                'interface_status': interface_status
            }), 500
        return jsonify(networks)
    except Exception as e:
        logger.error(f"Unexpected error during network scan: {str(e)}")
        return jsonify({
            'success': False, 
            'error': 'Internal server error',
            'interface_status': interface_status
        }), 500
        
        
@scan_bp.route('/sniff_probe_requests')
def sniff_probe_requests():
    """
    Sniff for probe requests on the configured interface.
    
    Query Parameters:
        interface (str): Optional. Network interface to use
        duration (int): Optional. Duration to sniff in seconds (5-60)
    
    Returns:
        JSON array of detected SSIDs
    """
    interface = request.args.get('interface', config['interface'])
    
    try:
        # Get duration from query params, default to 20 seconds
        duration = request.args.get('duration', '20')
        duration = int(duration)
        
        # Validate duration
        if duration < 5 or duration > 60:
            return jsonify({
                'success': False,
                'error': 'Duration must be between 5 and 60 seconds'
            }), 400
            
        ssids = network_utils.sniff_probe_requests(interface, duration)
        return jsonify(ssids)
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid duration parameter'
        }), 400
    except Exception as e:
        logger.error(f"Error sniffing probe requests: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500