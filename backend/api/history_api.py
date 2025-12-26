"""
History API Module - Truy vấn lịch sử giao dịch
"""
from flask import Blueprint, jsonify
from core.database.database import BlockchainDB

history_api = Blueprint('history_api', __name__)
db = BlockchainDB()

@history_api.route('/address/<address>', methods=['GET'])
def get_address_history(address):
    """Lấy danh sách giao dịch của một địa chỉ."""
    try:
        history = db.get_transactions_by_address(address)
        return jsonify({
            'success': True,
            'address': address,
            'history': history
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@history_api.route('/tx/<txid>', methods=['GET'])
def get_transaction_details(txid):
    """Lấy chi tiết một giao dịch theo TXID."""
    try:
        details = db.get_transaction_by_id(txid)
        if details:
            return jsonify({
                'success': True,
                'txid': txid,
                'details': details
            })
        else:
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@history_api.route('/balance/<address>', methods=['GET'])
def get_balance_history(address):
    """Lấy lịch sử số dư của một địa chỉ."""
    try:
        from core.database.database import BalanceDB
        bal_db = BalanceDB()
        history = bal_db.get_history(address)
        current_bal = bal_db.get_latest_balance(address)
        
        return jsonify({
            'success': True,
            'address': address,
            'current_balance': current_bal,
            'history': history
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
