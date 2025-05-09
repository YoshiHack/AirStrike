from flask import Flask, render_template, jsonify
import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import shared variables
from web.shared import *

# Create Flask app
from web import create_app
app = create_app()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard_stats')
def dashboard_stats():
    return jsonify(stats)

# Run the application
if __name__ == '__main__':
    # Create output directory if it doesn't exist
    os.makedirs(config['output_dir'], exist_ok=True)
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
