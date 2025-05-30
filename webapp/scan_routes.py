# AirStrike/webapp/scan_routes.py
from flask import Blueprint, jsonify, request, render_template, current_app

# Import the service functions from the network_service module
# The '.' means import from the current package ('webapp'), then 'services' sub-package.
from .services import network_service

# Define the Blueprint for scan-related routes
# 'scan' is the name of the blueprint, used internally by Flask (e.g., for url_for)
# template_folder='templates' tells Flask where to look for this blueprint's templates.
# If your templates are in webapp/templates/, this is usually handled by the app's default.
scan_bp = Blueprint('scan', __name__, template_folder='templates')


@scan_bp.route('/')  # This will be mapped to /scan/ if url_prefix='/scan' is set during registration
def show_scan_page():
    """
    Renders the main network scanning page (scan.html).
    """
    current_app.logger.info("Route: GET /scan/ - Rendering scan page.")
    # You can pass initial data to the template if needed, e.g., current interface
    current_interface = current_app.config.get('DEFAULT_INTERFACE', 'wlan0')
    return render_template('scan.html', current_interface=current_interface)


@scan_bp.route('/scan_wifi')  # Mapped to /scan/scan_wifi
def scan_wifi_endpoint():
    """
    API endpoint to perform a Wi-Fi scan or check interface status.
    Query Parameters:
        interface (str, optional): The interface to use. Defaults to app config.
        check_only (str, optional): If 'true', only checks interface status.
    """
    interface_name = request.args.get('interface', current_app.config['DEFAULT_INTERFACE'])
    check_only_flag = request.args.get('check_only', 'false').lower() == 'true'

    current_app.logger.info(
        f"Route: GET /scan/scan_wifi - Interface: '{interface_name}', Check Only: {check_only_flag}"
    )

    # Always get detailed interface status first
    interface_status = network_service.check_interface_status_detailed(interface_name)
    current_app.logger.debug(f"Interface status for '{interface_name}': {interface_status}")

    if check_only_flag:
        return jsonify({
            'success': True, # The operation of checking status was successful
            'interface_status': interface_status
        })

    # If not check_only, proceed with the Wi-Fi scan
    # The service function handles mode switching (managed for iwlist, then restore)
    scanned_networks, error = network_service.scan_wifi_networks_service(interface_name)

    if error:
        current_app.logger.error(f"Error during Wi-Fi scan on '{interface_name}': {error}")
        return jsonify({
            'success': False,
            'error': error,
            'interface_status': interface_status # Good to return this even on scan failure
        }), 500 # Or a more specific error code if applicable

    current_app.logger.info(f"Scan on '{interface_name}' successful, found {len(scanned_networks)} networks.")
    return jsonify(scanned_networks) # Returns a JSON array of network objects


@scan_bp.route('/sniff_probe_requests') # Mapped to /scan/sniff_probe_requests
def sniff_probe_requests_endpoint():
    """
    API endpoint to sniff for Wi-Fi probe requests.
    Query Parameters:
        interface (str, optional): The interface to use. Defaults to app config.
        duration (str, optional): Duration for sniffing in seconds. Defaults to 20.
    """
    interface_name = request.args.get('interface', current_app.config['DEFAULT_INTERFACE'])
    duration_str = request.args.get('duration', str(current_app.config.get('DEFAULT_SCAN_DURATION', 20)))

    current_app.logger.info(
        f"Route: GET /scan/sniff_probe_requests - Interface: '{interface_name}', Duration: {duration_str}s"
    )

    try:
        duration_seconds = int(duration_str)
        # Validate duration (e.g., 5 to 600 seconds)
        if not (5 <= duration_seconds <= 600):
            msg = "Duration for probe sniffing must be an integer between 5 and 600 seconds."
            current_app.logger.warning(f"Invalid duration: {duration_seconds}. {msg}")
            return jsonify({'success': False, 'error': msg}), 400
    except ValueError:
        msg = "Invalid duration format. Must be an integer."
        current_app.logger.warning(f"Invalid duration string: '{duration_str}'. {msg}")
        return jsonify({'success': False, 'error': msg}), 400

    # Call the service function for sniffing probe requests
    ssids_found, error = network_service.sniff_probe_requests_service(interface_name, duration_seconds)

    if error:
        current_app.logger.error(f"Error sniffing probe requests on '{interface_name}': {error}")
        return jsonify({'success': False, 'error': error}), 500

    current_app.logger.info(f"Probe sniffing on '{interface_name}' found {len(ssids_found)} SSIDs.")
    return jsonify(ssids_found) # Returns a JSON array of SSID strings
