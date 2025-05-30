# AirStrike/webapp/main_routes.py
from flask import Blueprint, render_template, jsonify, current_app

# Define the blueprint for main application routes (e.g., dashboard)
main_bp = Blueprint(
    'main',
    __name__,
    template_folder='templates' # Specifies where to look for templates for this blueprint
                                # Flask also checks app-level 'templates' folder.
)

# --- In-memory store for simple stats (Replace with a proper service/database for a real app) ---
# This is a very basic way to handle stats. For a more robust solution,
# consider a dedicated stats service or integrating with your attack/scan services.
_app_stats = {
    'networks_scanned_session': 0, # Example: reset per session or manage differently
    'attacks_launched_session': 0,
    'handshakes_captured_total': 0, # Example: could be persistent
    'current_interface': 'N/A'
}

def update_networks_scanned_stat(count):
    """Updates the number of networks scanned."""
    _app_stats['networks_scanned_session'] = count
    current_app.logger.info(f"Stats: Networks Scanned updated to {count}")

def increment_attacks_launched_stat():
    """Increments the count of attacks launched."""
    _app_stats['attacks_launched_session'] += 1
    current_app.logger.info(f"Stats: Attacks Launched incremented to {_app_stats['attacks_launched_session']}")

def update_handshakes_captured_stat(count):
    """Updates the total number of handshakes captured."""
    # This would typically be called from your attack service when a handshake is confirmed.
    _app_stats['handshakes_captured_total'] = count # Or += count
    current_app.logger.info(f"Stats: Handshakes Captured updated to {count}")


# --- Routes ---
@main_bp.route('/')
def index():
    """
    Serves the main dashboard page (index.html).
    """
    current_app.logger.info(f"Accessing dashboard (index.html). Current interface from config: {current_app.config.get('DEFAULT_INTERFACE')}")
    # Pass any necessary data to the template
    _app_stats['current_interface'] = current_app.config.get('DEFAULT_INTERFACE', 'N/A')
    return render_template('index.html', stats=_app_stats)

@main_bp.route('/dashboard_stats')
def get_dashboard_stats():
    """
    API endpoint to fetch current dashboard statistics.
    This can be called by JavaScript to dynamically update the dashboard.
    """
    current_app.logger.debug("Dashboard stats requested via API.")
    # Ensure the current interface is up-to-date from config
    _app_stats['current_interface'] = current_app.config.get('DEFAULT_INTERFACE', 'N/A')
    return jsonify(_app_stats)

# Example: A route to clear session stats (for demonstration)
@main_bp.route('/clear_session_stats', methods=['POST'])
def clear_session_stats():
    _app_stats['networks_scanned_session'] = 0
    _app_stats['attacks_launched_session'] = 0
    current_app.logger.info("Session stats cleared.")
    return jsonify(success=True, message="Session stats cleared.", current_stats=_app_stats)

