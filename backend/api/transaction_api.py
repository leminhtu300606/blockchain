"""
API endpoints for transaction verification and related operations.
"""
from flask import Blueprint, request, jsonify
from core.transaction_verifier import TransactionVerifier
from core.Tx import Tx, TxIn, TxOut, Script

# Create a Blueprint for transaction-related API endpoints
tx_api = Blueprint('transaction_api', __name__)

@tx_api.route('/verify', methods=['POST'])
def verify_transaction():
    """
    Verify a transaction's validity.
    
    Expected JSON payload:
    {
        "version": 1,
        "tx_ins": [
            {
                "prev_tx": "previous_tx_hash",
                "prev_index": 0,
                "script_sig": ["signature", "public_key"],
                "sequence": 0xffffffff
            }
        ],
        "tx_outs": [
            {
                "amount": 1000000,  # in satoshis
                "script_pubkey": ["OP_DUP", "OP_HASH160", "pubkey_hash", "OP_EQUALVERIFY", "OP_CHECKSIG"]
            }
        ],
        "locktime": 0,
        "utxo_set": {
            "previous_tx_hash": {
                0: {
                    "amount": 1000000,
                    "script_pubkey": ["OP_DUP", "OP_HASH160", "pubkey_hash", "OP_EQUALVERIFY", "OP_CHECKSIG"]
                }
            }
        }
    }
    """
    try:
        data = request.get_json()
        
        # Convert JSON data to Tx object
        tx_ins = [
            TxIn(
                prev_tx=tx_in['prev_tx'],
                prev_index=tx_in['prev_index'],
                script_sig=Script(tx_in.get('script_sig', [])),
                sequence=tx_in.get('sequence', 0xffffffff)
            )
            for tx_in in data.get('tx_ins', [])
        ]
        
        tx_outs = [
            TxOut(
                amount=tx_out['amount'],
                script_pubkey=Script(tx_out.get('script_pubkey', []))
            )
            for tx_out in data.get('tx_outs', [])
        ]
        
        tx = Tx(
            version=data.get('version', 1),
            tx_ins=tx_ins,
            tx_outs=tx_outs,
            locktime=data.get('locktime', 0)
        )
        
        # Get UTXO set from request
        utxo_set = data.get('utxo_set', {})
        
        # Verify the transaction
        is_valid = TransactionVerifier.verify_transaction(tx, utxo_set)
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'txid': tx.id() if hasattr(tx, 'id') else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@tx_api.route('/verify/coinbase', methods=['POST'])
def verify_coinbase():
    """
    Verify a coinbase transaction.
    
    Expected JSON payload:
    {
        "version": 1,
        "tx_ins": [
            {
                "prev_tx": "0000000000000000000000000000000000000000000000000000000000000000",
                "prev_index": 0xffffffff,
                "script_sig": ["block_height"],
                "sequence": 0xffffffff
            }
        ],
        "tx_outs": [
            {
                "amount": 5000000000,  # 50 BTC in satoshis
                "script_pubkey": ["OP_DUP", "OP_HASH160", "miner_pubkey_hash", "OP_EQUALVERIFY", "OP_CHECKSIG"]
            }
        ],
        "locktime": 0,
        "block_height": 1
    }
    """
    try:
        data = request.get_json()
        
        # Convert JSON data to Tx object
        tx_ins = [
            TxIn(
                prev_tx=tx_in['prev_tx'],
                prev_index=tx_in['prev_index'],
                script_sig=Script(tx_in.get('script_sig', [])),
                sequence=tx_in.get('sequence', 0xffffffff)
            )
            for tx_in in data.get('tx_ins', [])
        ]
        
        tx_outs = [
            TxOut(
                amount=tx_out['amount'],
                script_pubkey=Script(tx_out.get('script_pubkey', []))
            )
            for tx_out in data.get('tx_outs', [])
        ]
        
        tx = Tx(
            version=data.get('version', 1),
            tx_ins=tx_ins,
            tx_outs=tx_outs,
            locktime=data.get('locktime', 0)
        )
        
        # Verify the coinbase transaction
        block_height = data.get('block_height', 0)
        is_valid = TransactionVerifier.verify_coinbase(tx, block_height)
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'txid': tx.id() if hasattr(tx, 'id') else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
