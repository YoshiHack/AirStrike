# AirStrike/run_web.py
import os
import sys
import logging # For initial logging before Flask app is fully set up

# --- Initial Checks and Path Configuration ---

# 1. Root Privilege Check
if os.geteuid() != 0:
    print("ERROR: AirStrike must be run with root privileges.")
    print("Please restart with: sudo python3 run_web.py")
    sys.exit(1)
print("INFO: Script running with root privileges.")

# 2. Python Path Setup
# Add the directory containing this script (project root) to Python's module search path.
# This allows Python to find packages like 'webapp', 'utils', 'core_attacks', and 'config'.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
print(f"INFO: Project root '{project_root}' added to sys.path.")

# --- Import Core Application Components ---
# It's good practice to wrap these in try-except to catch early import errors.
try:
    from webapp import create_app  # Imports the app factory from webapp/__init__.py
    # 'config' should be directly importable as 'config.py' is in the project_root
    import config as app_server_config
except ImportError as e:
    print(f"FATAL ERROR: Could not import critical modules: {e}")
    print("Please ensure 'config.py' and the 'webapp' directory (with __init__.py) exist at the project root.")
    sys.exit(1)

# --- Application Initialization ---
# Create the Flask application instance using the factory.
app = create_app()

# --- Main Execution Guard ---
if __name__ == '__main__':
    # This block runs only when the script is executed directly (not imported).
    print("\n" + "=" * 70)
    print("               AirStrike Web Interface - Starting Up")
    print("=" * 70)
    
    # Log some configuration values for verification
    app.logger.info(f"Flask App Name: {app.name}")
    app.logger.info(f"Flask Debug Mode: {app.debug}") # app.debug is set by create_app from config
    app.logger.info(f"Output Directory: {app.config.get('OUTPUT_DIR', 'Not Configured')}")
    app.logger.info(f"Default Wireless Interface: {app.config.get('DEFAULT_INTERFACE', 'Not Configured')}")
    
    print("\nINFO: Web interface will be accessible at:")
    print("      http://localhost:5000")
    print("      http://<your-machine-ip>:5000 (if firewall allows)")
    print("\nPress CTRL+C to stop the server.")
    print("-" * 70 + "\n")

    try:
        # Run the Flask development server.
        # host='0.0.0.0' makes the server accessible from any IP address on the machine,
        # not just localhost. This is useful for testing from other devices on your network.
        # port=5000 is the standard Flask development port.
        # debug=app.debug uses the debug setting from the app's configuration.
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=app.debug # Controlled by config.py
            # threaded=True # Can be useful for handling multiple requests if needed,
                           # but be careful with global state in attack threads.
        )
    except KeyboardInterrupt:
        print("\nINFO: Server shutting down gracefully...")
    except Exception as e:
        app.logger.error(f"Failed to start or run the Flask server: {e}", exc_info=True)
        print(f"ERROR: Could not start the server: {e}")
    finally:
        print("INFO: AirStrike server has stopped.")
