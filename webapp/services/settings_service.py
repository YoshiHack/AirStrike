# AirStrike/webapp/services/settings_service.py
from flask import current_app
import os # For path validation if needed

# This service is for managing application settings.
# For now, it will mostly interact with the Flask app's runtime configuration.
# If settings were persisted to a file or database, this service would handle that.

def get_current_settings():
    """
    Retrieves current operational settings from the app configuration.
    """
    settings = {
        'default_interface': current_app.config.get('DEFAULT_INTERFACE', 'wlan0'),
        'default_wordlist': current_app.config.get('DEFAULT_WORDLIST', '/usr/share/wordlists/rockyou.txt'),
        'output_dir': current_app.config.get('OUTPUT_DIR', './captures'),
        # Add any other settings you want to expose
    }
    current_app.logger.info(f"Service: Retrieved current settings: {settings}")
    return settings

def update_setting_service(key, value):
    """
    Updates a specific setting in the application's runtime configuration.
    Note: This does not persist settings beyond the current server instance
          unless you add file/database saving logic here.
    Args:
        key (str): The configuration key to update (e.g., 'DEFAULT_INTERFACE').
        value (any): The new value for the setting.
    Returns:
        tuple: (success_bool, message_str)
    """
    allowed_keys = ['DEFAULT_INTERFACE', 'DEFAULT_WORDLIST', 'OUTPUT_DIR'] # Whitelist configurable keys

    if key not in allowed_keys:
        msg = f"Invalid setting key '{key}'. Not allowed to change."
        current_app.logger.warning(f"Service: {msg}")
        return False, msg

    # Optional: Add validation for values
    if key == 'DEFAULT_WORDLIST' and value and not os.path.isfile(value):
        # Basic check if wordlist file exists. More robust validation might be needed.
        # This check assumes the Flask server has permissions to check the path.
        # If running in a container or restricted env, this might not work as expected.
        # msg = f"Wordlist path '{value}' does not exist or is not a file."
        # current_app.logger.warning(f"Service: {msg}")
        # return False, msg
        current_app.logger.warning(f"Service: Wordlist path '{value}' provided. Existence check skipped in service for now.")


    if key == 'OUTPUT_DIR' and value:
        try:
            os.makedirs(value, exist_ok=True) # Attempt to create if it doesn't exist
            current_app.config[key] = os.path.abspath(value) # Store absolute path
        except OSError as e:
            msg = f"Error setting output directory '{value}': {e}"
            current_app.logger.error(f"Service: {msg}")
            return False, msg
    else:
        current_app.config[key] = value
    
    msg = f"Setting '{key}' updated to '{current_app.config[key]}' in runtime configuration."
    current_app.logger.info(f"Service: {msg}")

    # If you update DEFAULT_INTERFACE, also update the stats in main_routes for consistency
    if key == 'DEFAULT_INTERFACE':
        from webapp.main_routes import _app_stats # Be cautious with direct global/module var access
        _app_stats['current_interface'] = value

    return True, msg

# Example: If you had a function to save config to a file
# def save_settings_to_file_service():
#     try:
#         with open(os.path.join(current_app.config['PROJECT_ROOT'], 'user_config.py'), 'w') as f:
#             f.write(f"DEFAULT_INTERFACE = '{current_app.config['DEFAULT_INTERFACE']}'\n")
#             f.write(f"DEFAULT_WORDLIST = '{current_app.config['DEFAULT_WORDLIST']}'\n")
#             f.write(f"OUTPUT_DIR = '{current_app.config['OUTPUT_DIR']}'\n")
#         current_app.logger.info("Service: Settings saved to user_config.py")
#         return True, "Settings saved to file."
#     except Exception as e:
#         current_app.logger.error(f"Service: Error saving settings to file: {e}")
#         return False, f"Error saving settings: {e}"

