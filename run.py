#!/usr/bin/env python3
"""
AirStrike Web Interface Runner
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app
from web.app import app

if __name__ == '__main__':
    # Create output directory if it doesn't exist
    from web.shared import config
    os.makedirs(config['output_dir'], exist_ok=True)
    
    # Run the Flask app 
    app.run(debug=True, host='0.0.0.0', port=5000) 