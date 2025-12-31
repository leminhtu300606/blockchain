"""
Blockchain API Server - Cầu nối giữa Frontend và Backend

Cung cấp REST API để frontend giao tiếp với blockchain.

Chạy: python frontend/api.py
Truy cập: http://localhost:5000
"""
import sys
import os
import time
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from client.account import Account, generate_account
from core.blockchain import Blockchain
from core.database.database import BlockchainDB, UTXOSet
from core.mempool import mempool
from core.Tx import Tx, TxIn, TxOut, Script

# =============================================================================
# FLASK APP SETUP
# =============================================================================

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Cho phép cross-origin requests


# =============================================================================
# STATIC FILES
# =============================================================================

@app.route('/')
def serve_index():
    """Phục vụ trang chủ."""
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Phục vụ các file tĩnh."""
    return send_from_directory('.', path)


# =============================================================================
# WALLET API
# =============================================================================

@app.route('/api/wallet/create', methods=['POST'])
def create_wallet():
    """Tạo ví mới."""
    try:
        keys = generate_account()
        return jsonify({
            'success': True,
            'data': {
                'privateKey': keys['private_key'],
                'publicKey': keys['public_key'],
                'address': keys['address']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/wallet/import', methods=['POST'])
def import_wallet():
    """Import ví từ private key."""
    try:
        data = request.get_json()
        private_key = data.get('privateKey', '')
        
        if len(private_key) != 64:
            return jsonify({'success': False, 'error': 'Private key phải có 64 ký tự hex'}), 400
        
        account = Account(private_key=private_key)
        keys = account.create_keys()
        
        return jsonify({
            'success': True,
            'data': {
                'publicKey': keys['public_key'],
                'address': keys['address']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/wallet/balance/<address>', methods=['GET'])
def get_balance(address):
    """Lấy số dư của địa chỉ."""
    try:
        from core.database.database import UTXOSet
        utxo_set = UTXOSet()
        balance = utxo_set.get_balance(address)
        
        # UTXO model doesn't easily support history without an indexer
        # For now, we return current balance
        
        return jsonify({
            'success': True,
            'data': {
                'address': address,
                'balance': balance,
                'balanceBTC': balance / (10 ** 8),
                'history': [] 
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# TRANSACTION API
# =============================================================================

@app.route('/api/transaction/send', methods=['POST'])
def send_transaction():
    """Tạo và gửi giao dịch."""
    try:
        data = request.get_json()
        
        recipient = data.get('recipient', '')
        amount = int(data.get('amount', 0))
        sender_address = data.get('senderAddress', '')
        prev_txid = data.get('prevTxid', '0' * 64)
        prev_index = int(data.get('prevIndex', 0))
        input_amount = int(data.get('inputAmount', amount))
        
        if not recipient or amount <= 0:
            return jsonify({'success': False, 'error': 'Thông tin không hợp lệ'}), 400
        
        # Tạo transaction
        tx_out = TxOut(
            amount=amount, 
            script_pubkey=Script([
                'OP_DUP', 'OP_HASH160', 
                recipient, 
                'OP_EQUALVERIFY', 'OP_CHECKSIG'
            ])
        )
        
        tx_in = TxIn(
            prev_tx=prev_txid,
            prev_index=prev_index,
            script_sig=Script([sender_address]),
            sequence=0xffffffff
        )
        
        tx = Tx(version=1, tx_ins=[tx_in], tx_outs=[tx_out], locktime=0)
        txid = tx.id()
        
        # Thêm vào mempool
        fee = max(0, input_amount - amount)
        mempool.transactions[txid] = {
            'tx': tx, 
            'timestamp': time.time(), 
            'fee': fee, 
            'size': 200
        }
        mempool._fee_heap.append((-fee/200, txid))
        
        return jsonify({
            'success': True,
            'data': {
                'txid': txid,
                'amount': amount,
                'fee': fee,
                'status': 'pending'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# BLOCKCHAIN API
# =============================================================================

@app.route('/api/blockchain/info', methods=['GET'])
def get_blockchain_info():
    """Lấy thông tin blockchain."""
    try:
        db = BlockchainDB()
        blocks = db.read()
        
        if not blocks:
            return jsonify({
                'success': True,
                'data': {'totalBlocks': 0, 'latestBlock': None}
            })
        
        last_block = blocks[-1]
        header = last_block.get('Blockheader', {})
        
        return jsonify({
            'success': True,
            'data': {
                'totalBlocks': len(blocks),
                'latestHeight': last_block.get('Height', len(blocks) - 1),
                'latestHash': header.get('blockhash', ''),
                'latestTimestamp': header.get('timestamp', 0),
                'difficulty': header.get('bits', ''),
                'mempoolSize': mempool.get_size()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/blockchain/blocks', methods=['GET'])
def get_blocks():
    """Lấy danh sách blocks."""
    try:
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        
        db = BlockchainDB()
        blocks = db.read()
        
        # Lấy blocks mới nhất
        blocks = blocks[::-1]  # Đảo ngược để mới nhất lên đầu
        blocks = blocks[offset:offset + limit]
        
        result = []
        for block in blocks:
            header = block.get('Blockheader', {})
            result.append({
                'height': block.get('Height', 0),
                'hash': header.get('blockhash', '')[:32] + '...',
                'timestamp': header.get('timestamp', 0),
                'txCount': block.get('Txcount', len(block.get('Txs', [])))
            })
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/blockchain/block/<int:height>', methods=['GET'])
def get_block(height):
    """Lấy chi tiết một block."""
    try:
        db = BlockchainDB()
        blocks = db.read()
        
        if height < 0 or height >= len(blocks):
            return jsonify({'success': False, 'error': 'Block không tồn tại'}), 404
        
        block = blocks[height]
        header = block.get('Blockheader', {})
        
        return jsonify({
            'success': True,
            'data': {
                'height': block.get('Height', height),
                'hash': header.get('blockhash', ''),
                'previousHash': header.get('previous_block_hash', ''),
                'merkleRoot': header.get('merkle_root', ''),
                'timestamp': header.get('timestamp', 0),
                'bits': header.get('bits', ''),
                'nonce': header.get('nonce', 0),
                'txCount': block.get('Txcount', len(block.get('Txs', []))),
                'transactions': block.get('Txs', [])[:5]  # Giới hạn 5 tx
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/blockchain/mine', methods=['POST'])
def mine_block():
    """Đào block mới."""
    try:
        bc = Blockchain()
        last_block = bc.fetch_last_block()
        
        if last_block is None:
            return jsonify({'success': False, 'error': 'Blockchain trống'}), 500
        
        new_height = last_block['Height'] + 1
        prev_hash = last_block['Blockheader']['blockhash']
        
        start_time = time.time()
        bc.add_block(new_height, prev_hash)
        elapsed = time.time() - start_time
        
        return jsonify({
            'success': True,
            'data': {
                'height': new_height,
                'time': round(elapsed, 2),
                'reward': 50
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 50)
    print("  BLOCKCHAIN API SERVER")
    print("  Truy cập: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
