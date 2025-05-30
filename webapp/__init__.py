# AirStrike/webapp/__init__.py
from flask import Flask, request, render_template
import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# --- Path Setup for Importing 'config' from Project Root ---
# This ensures that 'import config' correctly finds AirStrike/config.py
# 'os.path.dirname(__file__)' is 'AirStrike/webapp/'
# 'os.path.join(..., '..')' goes up one level to 'AirStrike/'
project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

try:
    import config as app_config # This now correctly imports AirStrike/config.py
except ImportError as e:
    print(f"CRITICAL ERROR in webapp/__init__.py: Cannot import 'config.py'. Ensure it exists in '{project_root_dir}'. Error: {e}")
    sys.exit(1) # Exit if config cannot be loaded, as it's essential.

def create_app():
    """
    Application factory function to create and configure the Flask app.
    """
    # Initialize Flask app. Instance_relative_config=True could be useful
    # if you had instance-specific configs, but not essential for this setup.
    app = Flask(__name__, instance_relative_config=False)

    # --- Load Configuration from config.py ---
    app.config['SECRET_KEY'] = app_config.SECRET_KEY
    app.config['DEBUG'] = app_config.DEBUG
    app.config['OUTPUT_DIR'] = app_config.OUTPUT_DIR
    app.config['DEFAULT_INTERFACE'] = app_config.DEFAULT_INTERFACE
    app.config['DEFAULT_WORDLIST'] = app_config.DEFAULT_WORDLIST
    app.config['LOG_LEVEL'] = getattr(app_config, 'LOG_LEVEL', 'INFO').upper()
    app.config['MAX_LOG_LINES_MEMORY'] = getattr(app_config, 'MAX_LOG_LINES_MEMORY', 200)


    # --- Setup Logging ---
    if not app.debug: # More comprehensive logging for non-debug mode
        log_file_path = os.path.join(app_config.PROJECT_ROOT, 'airstrike_webapp.log')
        file_handler = RotatingFileHandler(log_file_path, maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL'], logging.INFO))
        app.logger.addHandler(file_handler)
        # Also remove default Flask handler if you want only file logging in production
        # app.logger.removeHandler(default_handler)

    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL'], logging.INFO))
    app.logger.info('Flask application starting up...')
    app.logger.info(f"Output directory configured: {app.config['OUTPUT_DIR']}")


    # --- Import and Register Blueprints ---
    # These imports are relative to the current package ('webapp')
    try:
        from .main_routes import main_bp
        from .scan_routes import scan_bp
        from .attack_routes import attack_bp # Corrected name
        from .settings_routes import settings_bp # Added relative import
        from .result_routes import results_bp # Added relative import
        from .diagnostics_routes import diagnostics_bp # Added relative import
    except ImportError as e:
        app.logger.critical(f"Failed to import one or more blueprint modules: {e}", exc_info=True)
        # This is a critical error, so re-raise it to prevent the app from starting incorrectly.
        raise

    app.register_blueprint(main_bp)  # Root routes like '/'
    app.register_blueprint(scan_bp, url_prefix='/scan')
    app.register_blueprint(attack_bp, url_prefix='/attack') # Corrected name
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(results_bp, url_prefix='/results')
    app.register_blueprint(diagnostics_bp, url_prefix='/diagnostics')
    app.logger.info("All blueprints registered successfully.")

    # --- Error Handlers ---
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f"404 Not Found: {request.url} (Referred by: {request.referrer})")
        return render_template('error.html', error_code=404, error_message="Page Not Found", error_detail=str(error)), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"500 Internal Server Error: {request.url}", exc_info=error)
        return render_template('error.html', error_code=500, error_message="Internal Server Error", error_detail=str(error)), 500

    @app.errorhandler(Exception) # Generic error handler for unhandled exceptions
    def unhandled_exception(error):
        app.logger.error(f"Unhandled Exception: {request.url}", exc_info=error)
        # In debug mode, Flask might show its own debugger.
        # In production, you'd want a generic error page.
        return render_template('error.html', error_code="Unhandled", error_message="An unexpected error occurred", error_detail=str(error)), 500


    # --- Health Check Endpoint (Optional) ---
    @app.route('/health')
    def health():
        """Simple health check endpoint."""
        return "AirStrike WebApp is Healthy!", 200

    app.logger.info("Flask application created and configured.")
    return app
