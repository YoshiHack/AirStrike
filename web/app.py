from flask import Flask, render_template, jsonify, request
import os
import sys
import logging
import traceback

# Add the project root directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import shared variables
from web.shared import config, stats, logger

try:
    # Create Flask app
    from web import create_app
    app = create_app()

    # Ensure sudo status is up to date at startup
    from web.shared import is_sudo_authenticated
    is_sudo_authenticated()

    # Import and initialize SocketIO
    from web.socket_io import socketio, init_socketio
    init_socketio(app)

    # Set up Flask logger to use our custom logger
    app.logger.handlers = []
    for handler in logger.handlers:
        app.logger.addHandler(handler)
    app.logger.setLevel(logger.level)
    
    # Register error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        logger.warning(f"404 error: {request.path}")
        return render_template('error.html', error="Page not found"), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"500 error: {str(e)}")
        return render_template('error.html', error="Internal server error"), 500

    # Routes
    @app.route('/')
    def index():
        return render_template('index.html', sudo_configured=config.get('sudo_configured', False))

    @app.route('/dashboard_stats')
    def dashboard_stats():
        return jsonify(stats)

except Exception as e:
    logger.error(f"Error initializing application: {e}")
    logger.error(traceback.format_exc())
    raise

# Run the application
if __name__ == '__main__':
    try:
        # Create output directory if it doesn't exist
        os.makedirs(config['output_dir'], exist_ok=True)
        
        # Log application startup
        logger.info(f"Starting AirStrike web interface on port 5001")
        
        # Run the Flask app with SocketIO
        socketio.run(app, debug=False, host='0.0.0.0', port=5001)
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        logger.error(traceback.format_exc())
