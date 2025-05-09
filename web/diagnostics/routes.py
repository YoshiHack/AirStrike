from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from web.shared import logger, config, run_with_sudo
from .helpers import get_interface_details, get_system_info

diagnostics_bp = Blueprint('diagnostics', __name__)

@diagnostics_bp.route('/diagnostics')
def show_diagnostics():
    """Render the diagnostics page"""
    # Check if sudo is configured before rendering the page
    if not config.get('sudo_configured', False):
        # Redirect directly to sudo auth page
        return redirect(url_for('settings.sudo_auth', next=url_for('diagnostics.show_diagnostics')))
    
    # Get system info
    system_info = get_system_info()
    # Get interface details
    interface_details = get_interface_details(config['interface'])
    
    # Get available diagnostic commands
    diagnostic_commands = [
        {'name': 'iwconfig', 'description': 'Show wireless interfaces'},
        {'name': 'ifconfig', 'description': 'Show all interfaces'},
        {'name': 'ip a', 'description': 'Show all interfaces (modern version)'},
        {'name': f"iwlist {config['interface']} scanning", 'description': 'Scan for networks'},
        {'name': f"iw dev {config['interface']} scan", 'description': 'Alternative network scan'},
        {'name': 'rfkill list', 'description': 'Check for blocked interfaces'},
        {'name': 'lsmod | grep -E "^(cfg|mac|rtl|ath|iw)"', 'description': 'Show WiFi kernel modules'}
    ]
    
    return render_template('diagnostics.html', 
                          system_info=system_info,
                          interface_details=interface_details,
                          diagnostic_commands=diagnostic_commands)

@diagnostics_bp.route('/run_diagnostic', methods=['POST'])
def run_diagnostic():
    """Run a diagnostic command with sudo privileges"""
    # Check if sudo is configured
    if not config.get('sudo_configured', False):
        flash('Administrator privileges required', 'danger')
        return redirect(url_for('settings.sudo_auth', next=request.referrer or url_for('diagnostics.show_diagnostics')))
    
    command = request.form.get('command')
    if not command:
        flash('No command provided', 'danger')
        return redirect(url_for('diagnostics.show_diagnostics'))
    
    # Only allow certain safe diagnostic commands
    allowed_commands = [
        'iwconfig', 
        'ifconfig',
        'ip a',
        'iwlist',
        'iw dev',
        'rfkill list',
        'lsmod | grep -E "^(cfg|mac|rtl|ath|iw)"'
    ]
    
    # Check if the command is allowed
    command_allowed = False
    for allowed in allowed_commands:
        if command.startswith(allowed):
            command_allowed = True
            break
    
    if not command_allowed:
        flash(f'Command not allowed. Allowed commands: {", ".join(allowed_commands)}', 'danger')
        return redirect(url_for('diagnostics.show_diagnostics'))
    
    # Run the command
    success, output, error = run_with_sudo(command)
    
    # Show the result
    if success:
        result = output
        flash('Command executed successfully', 'success')
    else:
        result = f"Error: {error}"
        flash('Command failed', 'danger')
    
    return render_template('command_result.html', 
                          command=command, 
                          result=result,
                          success=success,
                          back_url=url_for('diagnostics.show_diagnostics')) 