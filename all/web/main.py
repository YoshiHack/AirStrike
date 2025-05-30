# main.py
import os
from flask import Flask, render_template, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Mocked stats for dashboard (replace with actual logic later)
stats = {
    'networks_count': 0,
    'attacks_count': 0,
    'captures_count': 0
}

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard_stats')
def dashboard_stats():
    return jsonify(stats)

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error="Internal server error"), 500

# Run the Flask app
if __name__ == '__main__':
    print("Starting AirStrike Web Dashboard...")
    print("Access it at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
