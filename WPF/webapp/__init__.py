# airstrike/webapp/__init__.py
from flask import Flask
import os
import sys

# Ensure project root is in path to find the main 'config.py'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config as app_config # Import your new config.py

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = app_config.SECRET_KEY
    app.config['DEBUG'] = app_config.DEBUG
    app.config['OUTPUT_DIR'] = app_config.OUTPUT_DIR
    app.config['DEFAULT_INTERFACE'] = app_config.DEFAULT_INTERFACE
    app.config['DEFAULT_WORDLIST'] = app_config.DEFAULT_WORDLIST

    # Initialize logging (can be a simple setup or use Flask's logger)
    # For simplicity, Flask's default logger is often enough for development.
    # You can configure it further if needed.

    # Register Blueprints (or define routes directly)
    from .main_routes import main_bp # Assuming you create this
    from .scan_routes import scan_bp
    from .attack_routes import attacks_bp
    from .settings_routes import settings_bp
    from .results_routes import results_bp
    from .diagnostics_routes import diagnostics_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(scan_bp, url_prefix='/scan') # Example prefix
    app.register_blueprint(attacks_bp, url_prefix='/attack')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(results_bp, url_prefix='/results')
    app.register_blueprint(diagnostics_bp, url_prefix='/diagnostics')
    
    # Error handlers (from your web/app.py)
    @app.errorhandler(404)
    def page_not_found(e):
        app.logger.warning(f"404 error: {request.path}")
        return render_template('error.html', error=f"Page {request.path} not found"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f"500 error: {str(e)}")
        return render_template('error.html', error=str(e)), 500

    return app