# AirStrike/webapp/diagnostics_routes.py
from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from .services import diagnostics_service
from .services import network_service # For getting interface list

diagnostics_bp = Blueprint('diagnostics', __name__, template_folder='templates')

@diagnostics_bp.route('/') # Mapped to /diagnostics/
def show_diagnostics_page():
    """
    Renders the main diagnostics page (diagnostics.html).
    """
    current_app.logger.info("Route: GET /diagnostics/ - Rendering diagnostics page.")
    
    system_info = diagnostics_service.get_system_info_service()
    default_interface = current_app.config.get('DEFAULT_INTERFACE', 'wlan0')
    interface_details = diagnostics_service.get_interface_diagnostics_service(default_interface)
    tool_availability = diagnostics_service.check_tool_availability_service()
    
    # Provide a list of common diagnostic commands for the user to select from
    # These should align with what run_diagnostic_command_service allows.
    # The actual command string will be sent by the form.
    selectable_commands = [
        {"name": "Interface Config (ip addr)", "cmd": "ip addr"},
        {"name": "Wireless Config (iwconfig)", "cmd": f"iwconfig {default_interface}"},
        {"name": "Wireless Details (iw dev)", "cmd": f"iw dev {default_interface} link"},
        {"name": "Routing Table (ip route)", "cmd": "ip route"},
        {"name": "RFKill Status (rfkill list)", "cmd": "rfkill list"},
        {"name": "NetworkManager Status (nmcli dev status)", "cmd": "nmcli dev status"},
        {"name": "Ping Gateway (example)", "cmd": "ping -c 3 $(ip route | grep default | awk '{print $3}' | head -n 1)"}, # More dynamic
        {"name": "List Network PCI Devices", "cmd": "lspci -nnk | grep -i network"},
        {"name": "List USB WLAN Adapters", "cmd": "lsusb | grep -i -e wlan -e wireless"},
        {"name": "Kernel Log Tail (dmesg)", "cmd": "dmesg | tail -n 30"},
    ]
    
    # Get available interfaces to allow user to select for some commands
    available_interfaces = network_service.get_available_interfaces_service()


    return render_template(
        'diagnostics.html',
        system_info=system_info,
        interface_details=interface_details, # Details for the default interface
        tool_availability=tool_availability,
        selectable_commands=selectable_commands,
        default_interface=default_interface,
        available_interfaces=available_interfaces
    )

@diagnostics_bp.route('/run_command', methods=['POST']) # Mapped to /diagnostics/run_command
def run_diagnostic_command_endpoint():
    """
    API endpoint (or form submission handler) to run a diagnostic command.
    """
    command_to_run = request.form.get('command_str') # From a text input
    selected_command_template = request.form.get('selected_command_template') # From dropdown
    command_interface_target = request.form.get('command_interface_target', current_app.config.get('DEFAULT_INTERFACE'))


    if selected_command_template: # User chose from dropdown
        # Substitute interface placeholder if present
        command_to_run = selected_command_template.replace("{interface}", command_interface_target)
    elif not command_to_run: # No command provided at all
        flash("No diagnostic command was provided.", "warning")
        return redirect(url_for('diagnostics.show_diagnostics_page'))

    current_app.logger.info(f"Route: POST /diagnostics/run_command - Command: '{command_to_run}'")

    success, output, error_output = diagnostics_service.run_diagnostic_command_service(command_to_run)
    
    # Render a result page or return JSON
    # For simplicity, let's use the command_result.html template you had.
    # You'll need to create/ensure this template exists in webapp/templates/
    return render_template(
        'command_result.html',
        command_executed=command_to_run,
        command_output=output if success else f"Error Output:\n{error_output}\n\nStandard Output (if any):\n{output}",
        was_successful=success,
        back_url=url_for('diagnostics.show_diagnostics_page') # URL to go back to diagnostics
    )

# You can add more specific diagnostic API endpoints if needed, e.g.,
# @diagnostics_bp.route('/api/system_info')
# def api_get_system_info():
#     return jsonify(diagnostics_service.get_system_info_service())

# @diagnostics_bp.route('/api/interface_info/<interface_name>')
# def api_get_interface_info(interface_name):
#     return jsonify(diagnostics_service.get_interface_diagnostics_service(interface_name))

# @diagnostics_bp.route('/api/tool_check')
# def api_tool_check():
#     return jsonify(diagnostics_service.check_tool_availability_service())
