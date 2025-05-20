from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from web.shared import *
from .helpers import (
    get_available_interfaces, 
    save_interface_setting, 
    save_wordlist_setting, 
    save_output_dir_setting
)

settings_bp = Blueprint('settings', __name__)
@settings_bp.route('/settings')
def show_settings():
    # Get available interfaces
    interfaces = get_available_interfaces()
    return render_template('settings.html', 
                          interfaces=interfaces, 
                          current_interface=config['interface'],
                          default_wordlist=config['wordlist'],
                          output_dir=config['output_dir'],
                          sudo_configured=config.get('sudo_configured', False))

# API Endpoints


@settings_bp.route('/get_interfaces')
def get_interfaces():
    interfaces = get_available_interfaces()
    return jsonify({
        'interfaces': interfaces,
        'current_interface': config['interface']
    })

@settings_bp.route('/set_interface', methods=['POST'])
def set_interface():
    data = request.json
    if 'interface' in data:
        success = save_interface_setting(data['interface'])
        return jsonify({'success': success})
    return jsonify({'success': False, 'error': 'No interface provided'})

@settings_bp.route('/save_wordlist', methods=['POST'])
def save_wordlist():
    data = request.json
    if 'wordlist' in data:
        success = save_wordlist_setting(data['wordlist'])
        return jsonify({'success': success})
    return jsonify({'success': False, 'error': 'No wordlist provided'})

@settings_bp.route('/save_output_dir', methods=['POST'])
def save_output_dir():
    data = request.json
    if 'output_dir' in data:
        success = save_output_dir_setting(data['output_dir'])
        return jsonify({'success': success})
    return jsonify({'success': False, 'error': 'No output directory provided'})

@settings_bp.route('/sudo_auth', methods=['GET', 'POST'])
def sudo_auth():
    """Handle sudo password authentication"""
    error = None
    
    # If running as root, skip authentication
    if is_running_as_root():
        config['sudo_configured'] = True
        flash('Running as root. Sudo authentication not required.', 'success')
        redirect_to = request.args.get('next', url_for('settings.show_settings'))
        return redirect(redirect_to)
    
    if request.method == 'POST':
        password = request.form.get('password')
        if not password:
            flash('Password is required', 'danger')
            error = 'Password is required'
            return render_template('sudo_auth.html', next=request.args.get('next', '/'), error=error)
        
        # Test the password with a simple command that requires sudo
        success, output, error_msg = run_with_sudo("id -u", password)
        
        if success and output.strip() == "0":  # 0 is the user ID of root
            # Password is correct, save it
            config['sudo_password'] = password
            config['sudo_configured'] = True
            flash('Sudo authentication successful', 'success')
            
            # Redirect to the page they were trying to access
            redirect_to = request.args.get('next', url_for('settings.show_settings'))
            return redirect(redirect_to)
        else:
            error = 'Authentication failed: ' + (error_msg or 'Incorrect password')
            flash(error, 'danger')
            config['sudo_configured'] = False  # Ensure we mark as not configured
            return render_template('sudo_auth.html', next=request.args.get('next', '/'), error=error)
    
    # GET request - show the auth form
    return render_template('sudo_auth.html', next=request.args.get('next', '/'), error=error)
