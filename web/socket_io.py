"""
SocketIO module for AirStrike web interface.

This module provides the SocketIO instance used for real-time communication.
"""

from flask_socketio import SocketIO
import logging
import sys

# Configure basic logging if not already configured
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)

# Create SocketIO instance with error handling
try:
    # Initialize with async_mode='threading' for better compatibility
    socketio = SocketIO(cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=True)
    logging.info("SocketIO initialized successfully with threading mode")
except Exception as e:
    logging.error(f"Error initializing SocketIO: {e}")
    # Fallback to a basic instance
    try:
        socketio = SocketIO()
        logging.info("SocketIO initialized with default settings")
    except Exception as e:
        logging.error(f"Critical error initializing SocketIO: {e}")
        # Create a dummy socketio object that won't crash the app
        class DummySocketIO:
            def init_app(self, app): pass
            def run(self, app, **kwargs): 
                from flask import Flask
                if isinstance(app, Flask):
                    return app.run(**kwargs)
            def on(self, event): return lambda f: f
            def emit(self, event, data=None): pass
        
        socketio = DummySocketIO()
        logging.warning("Using dummy SocketIO implementation due to initialization errors")

def init_socketio(app):
    """
    Initialize SocketIO with the Flask app.
    
    Args:
        app: The Flask application instance
    """
    try:
        socketio.init_app(app)
        logging.info(f"SocketIO initialized with app {app.name}")
        
        @socketio.on('connect')
        def handle_connect():
            from web.shared import logger
            logger.info('Client connected')
            # Send a welcome message to confirm connection
            socketio.emit('welcome', {'message': 'Connected to AirStrike server'})

        @socketio.on('disconnect')
        def handle_disconnect():
            from web.shared import logger
            logger.info('Client disconnected')
            
        @socketio.on_error()
        def handle_error(e):
            from web.shared import logger
            logger.error(f"SocketIO error: {e}")
            
    except Exception as e:
        from web.shared import logger
        logger.error(f"Error initializing SocketIO events: {e}") 