from flask import Flask, render_template, jsonify, request, redirect, url_for
import sys
import os
import json
import logging
from datetime import datetime

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

# Import Blockchain core
from core.blockchain import Blockchain
from api.transaction_api import tx_api as transaction_api

# Initialize Flask app
app = Flask(__name__)

# Register Blueprints
app.register_blueprint(transaction_api, url_prefix='/api/transaction')

# Initialize Blockchain
# Note: This will load the chain from database or create new if empty
blockchain = Blockchain()

def format_block_for_frontend(block_data):
    """
    Helper function to convert backend block format to frontend expected format.
    """
    if not block_data:
        return None
        
    header = block_data.get('Blockheader', {})
    
    # Format timestamp
    ts = header.get('timestamp')
    timestamp_str = ""
    if ts:
        timestamp_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    return {
        'index': block_data.get('Height'),
        'hash': header.get('blockhash') or header.get('block_hash'),
        'previous_hash': header.get('previous_block_hash'),
        'timestamp': timestamp_str,
        'transactions': block_data.get('Txcount', 0),
        'difficulty': header.get('bits'),
        'nonce': header.get('nonce'),
        'merkle_root': header.get('merkle_root'),
        'size': block_data.get('Blocksize', 0),
        'version': header.get('version', 1)
    }

@app.route('/')
def index():
    """Home page - Show latest blocks."""
    # Reload chain data to get latest updates
    # Note: In production, we might want a efficient way than reading full file
    # For now, rely on database caching
    all_blocks = blockchain.db.read()
    
    # Sort by height desc (newest first)
    sorted_blocks = sorted(all_blocks, key=lambda x: int(x.get('Block', 0)) if 'Block' in x else x.get('Height', 0), reverse=True)
    
    # Format top 5 blocks
    latest_blocks = []
    for b in sorted_blocks[:5]:
        # Normalize/Format block data
        # The db.read() might return raw dicts matching file structure or normalized ones
        # Use blockchain.db._normalize_block() logic or similar if needed
        # But wait, db.read() returns list of dicts. Let's rely on standard format
        # If db.read() returns raw strings keys like "Block", "Hash", we need to handle that.
        # Let's check database.py read() again. It returns keys like "Block", "Hash", "Timestamp".
        
        # To be safe, let's use the provided normalize method if accessible or handle raw keys
        normalized = blockchain.db._normalize_block(b)
        latest_blocks.append(format_block_for_frontend(normalized))
        
    return render_template('index.html', latest_blocks=latest_blocks)

@app.route('/blocks')
def blocks():
    """All blocks page."""
    all_blocks_raw = blockchain.db.read()
    formatted_blocks = []
    
    # Sort newest first
    sorted_blocks = sorted(all_blocks_raw, key=lambda x: int(x.get('Block', 0)) if 'Block' in x else x.get('Height', 0), reverse=True)

    for b in sorted_blocks:
        normalized = blockchain.db._normalize_block(b)
        formatted_blocks.append(format_block_for_frontend(normalized))
        
    return render_template('blocks.html', blocks=formatted_blocks)

@app.route('/block/<int:block_index>')
def block_detail(block_index):
    """Block detail page."""
    block_data = blockchain.db.get_block_by_height(block_index)
    
    if block_data is None:
        return "Block not found", 404
        
    formatted_block = format_block_for_frontend(block_data)
    return render_template('block_detail.html', block=formatted_block)

@app.route('/verify')
def verify_transaction_page():
    """Render the transaction verification page."""
    return render_template('verify_transaction.html')

@app.route('/history')
@app.route('/history/<address>')
def history(address=None):
    """Transaction history page."""
    if address:
        # Fetch transaction history
        tx_history = blockchain.db.get_transactions_by_address(address)
        
        # Fetch balance history from BalanceDB
        from core.database.database import BalanceDB
        bal_db = BalanceDB()
        balance_history = bal_db.get_history(address)
        current_balance = bal_db.get_latest_balance(address)
        
        return render_template('history.html', 
                             address=address, 
                             history=tx_history,
                             balance_history=balance_history,
                             current_balance=current_balance)
    
    return render_template('history.html', address=None, history=[], balance_history=[], current_balance=0)

if __name__ == '__main__':
    # Use port 5001 to avoid conflict with standard 5000
    app.run(debug=True, port=5001)
