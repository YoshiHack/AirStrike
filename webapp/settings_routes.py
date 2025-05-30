# AirStrike/webapp/settings_routes.py
from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from .services import settings_service # For getting/setting configurations
from .services import network_service # For getting available interfaces

settings_bp = Blueprint('settings', __name__, template_folder='templates')

@settings_bp.route('/') # Mapped to /settings/
def show_settings_page():
    """
    Renders the settings page (settings.html).
    """
    current_app.logger.info("Route: GET /settings/ - Rendering settings page.")
    current_settings = settings_service.get_current_settings()
    available_interfaces = network_service.get_available_interfaces_service()
    
    # Add 'is_root' to the context for the template
    # Your original template had a notice about administrator privileges.
    is_root = os.geteuid() == 0 if hasattr(os, 'geteuid') else False # Handle non-POSIX systems gracefully

    return render_template(
        'settings.html',
        settings=current_settings,
        interfaces=available_interfaces,
        current_interface=current_settings.get('default_interface'),
        is_root=is_root # Pass root status to template
    )

@settings_bp.route('/get_interfaces', methods=['GET']) # Mapped to /settings/get_interfaces
def get_interfaces_endpoint():
    """
    API endpoint to get available network interfaces and current default.
    """
    current_app.logger.info("Route: GET /settings/get_interfaces - Fetching interfaces.")
    interfaces = network_service.get_available_interfaces_service()
    current_interface = current_app.config.get('DEFAULT_INTERFACE')
    return jsonify({
        'success': True,
        'interfaces': interfaces,
        'current_interface': current_interface
    })

@settings_bp.route('/update', methods=['POST']) # Mapped to /settings/update
def update_settings_endpoint():
    """
    API endpoint to update a specific setting.
    Expects JSON: {"key": "SETTING_NAME", "value": "new_value"}
    """
    current_app.logger.info("Route: POST /settings/update - Request to update setting.")
    data = request.get_json()

    if not data or 'key' not in data or 'value' not in data:
        current_app.logger.warning("Bad Request: Missing 'key' or 'value' for settings update.")
        return jsonify(success=False, error="Invalid request: 'key' and 'value' are required."), 400

    key = data['key']
    value = data['value']
    
    current_app.logger.info(f"Attempting to update setting '{key}' to '{value}'.")
    success, message = settings_service.update_setting_service(key, value)

    if success:
        # flash(message, 'success') # Flashing is for server-rendered redirects
        return jsonify(success=True, message=message)
    else:
        # flash(message, 'danger')
        return jsonify(success=False, error=message), 400 # Or 500 if it's an internal error

# Example: Route for saving settings to a file (if implemented in service)
# @settings_bp.route('/save_to_file', methods=['POST'])
# def save_settings_to_file_endpoint():
#     current_app.logger.info("Route: POST /settings/save_to_file - Request to save settings to file.")
#     success, message = settings_service.save_settings_to_file_service()
#     if success:
#         return jsonify(success=True, message=message)
#     else:
#         return jsonify(success=False, error=message), 500

