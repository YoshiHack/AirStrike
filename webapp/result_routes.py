# AirStrike/webapp/results_routes.py
from flask import Blueprint, render_template, jsonify, current_app, request
from .services import attack_service # To get status of attacks

results_bp = Blueprint('results', __name__, template_folder='templates')

@results_bp.route('/') # Mapped to /results/
def show_results_page():
    """
    Renders the main results page (results.html).
    This page will typically use JavaScript to poll for attack status and logs.
    """
    current_app.logger.info("Route: GET /results/ - Rendering results page.")
    # Optionally, pass a list of active/recent attacks to the template
    # so the user can select one to view, or default to the latest.
    active_attacks_summary = attack_service.get_all_active_attacks_service()
    
    # Determine if there's a specific attack_id to focus on (e.g., from query param or session)
    # For simplicity, the JS on results.html will likely handle which attack to poll.
    # focused_attack_id = request.args.get('attack_id')

    return render_template('results.html', attacks_summary=active_attacks_summary)


# The actual status and log fetching will be done via endpoints in attack_routes.py:
# - GET /attack/status/<attack_id>
# - GET /attack/active_attacks

# If you had specific data related to results (e.g., saved handshakes, reports),
# you would add routes and services here to retrieve and display them.

# Example: Route to list captured handshakes (if you implement a service for it)
# from .services.results_service import get_captured_handshakes_service # Create this service

# @results_bp.route('/captured_handshakes_list')
# def list_captured_handshakes_endpoint():
#     current_app.logger.info("Route: GET /results/captured_handshakes_list - Fetching handshakes.")
#     handshakes, error = get_captured_handshakes_service() # This service would scan OUTPUT_DIR
#     if error:
#         return jsonify(success=False, error=error), 500
#     return jsonify(success=True, handshakes=handshakes)

