# airstrike/run_web.py
import os
import sys

# Ensure the script is running with root privileges
if os.getpid() != 0:
    print("ERROR: AirStrike must be run with root privileges.")
    print("Please restart with: sudo python run_web.py")
    sys.exit(1)

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webapp import create_app

app = create_app()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Starting AirStrike Web Interface")
    print("Access the web interface at: http://localhost:5000")
    print("=" * 60 + "\n")
    app.run(debug=app.config.get('DEBUG', True), host='0.0.0.0', port=5000)