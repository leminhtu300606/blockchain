from flask import Flask, render_template, jsonify, request, redirect, url_for
import sys
import os
import json

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

app = Flask(__name__)

# Import and register the transaction API blueprint
from api.transaction_api import tx_api as transaction_api
app.register_blueprint(transaction_api, url_prefix='/api/transaction')

# Mock data for demonstration
BLOCKS = [
    {
        'index': 1,
        'hash': '0000000000000000000abc123...',
        'previous_hash': '0000000000000000000def456...',
        'timestamp': '2025-12-15 08:35:00',
        'transactions': 5,
        'difficulty': 4,
        'nonce': 12345,
        'merkle_root': 'abc123def456...',
        'size': 1024,
        'version': 1
    },
    # Add more mock blocks as needed
]

@app.route('/')
def index():
    return render_template('index.html', latest_blocks=BLOCKS[:5])

@app.route('/blocks')
def blocks():
    return render_template('blocks.html', blocks=BLOCKS)

@app.route('/block/<int:block_index>')
def block_detail(block_index):
    block = next((b for b in BLOCKS if b['index'] == block_index), None)
    if block is None:
        return "Block not found", 404
    return render_template('block_detail.html', block=block)

@app.route('/verify')
def verify_transaction_page():
    """Render the transaction verification page"""
    return render_template('verify_transaction.html')

# New endpoint to verify a transaction via the frontend
@app.route('/verify-transaction', methods=['POST'])
def verify_transaction_ui():
    """
    Frontend endpoint to verify a transaction.
    This is a wrapper around the API endpoint for better error handling.
    """
    try:
        # Forward the request to the API endpoint
        import requests
        response = requests.post(
            'http://localhost:5000/api/transaction/verify',
            json=request.json,
            headers={'Content-Type': 'application/json'}
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error verifying transaction: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Changed port to avoid conflicts with other services
