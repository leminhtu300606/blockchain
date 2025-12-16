"""
Transaction API Module - REST API cho xác thực giao dịch

Module này cung cấp các API endpoints để:
- Xác thực transaction thông thường
- Xác thực coinbase transaction

Endpoints:
- POST /verify: Xác thực một transaction
- POST /verify/coinbase: Xác thực một coinbase transaction
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any, List

from core.transaction_verifier import TransactionVerifier
from core.Tx import Tx, TxIn, TxOut, Script


# =============================================================================
# BLUEPRINT SETUP
# =============================================================================

# Blueprint cho các API liên quan đến transaction
tx_api = Blueprint('transaction_api', __name__)


# =============================================================================
# HELPER FUNCTIONS - Tái sử dụng code chung
# =============================================================================

def parse_transaction_from_json(data: Dict[str, Any]) -> Tx:
    """
    Parse JSON data thành Tx object.
    
    Hàm helper này được sử dụng bởi cả verify_transaction() và verify_coinbase()
    để tránh duplicate code.
    
    Args:
        data: Dictionary chứa dữ liệu transaction từ JSON request
        
    Returns:
        Tx: Transaction object đã được parse
        
    Expected JSON format:
        {
            "version": 1,
            "tx_ins": [
                {
                    "prev_tx": "hash...",
                    "prev_index": 0,
                    "script_sig": ["sig", "pubkey"],
                    "sequence": 0xffffffff
                }
            ],
            "tx_outs": [
                {
                    "amount": 1000000,
                    "script_pubkey": ["OP_DUP", "OP_HASH160", "hash", "OP_EQUALVERIFY", "OP_CHECKSIG"]
                }
            ],
            "locktime": 0
        }
    """
    # Parse inputs
    tx_ins: List[TxIn] = []
    for tx_in_data in data.get('tx_ins', []):
        tx_in = TxIn(
            prev_tx=tx_in_data['prev_tx'],
            prev_index=tx_in_data['prev_index'],
            script_sig=Script(tx_in_data.get('script_sig', [])),
            sequence=tx_in_data.get('sequence', 0xffffffff)
        )
        tx_ins.append(tx_in)
    
    # Parse outputs
    tx_outs: List[TxOut] = []
    for tx_out_data in data.get('tx_outs', []):
        tx_out = TxOut(
            amount=tx_out_data['amount'],
            script_pubkey=Script(tx_out_data.get('script_pubkey', []))
        )
        tx_outs.append(tx_out)
    
    # Tạo và trả về Tx object
    return Tx(
        version=data.get('version', 1),
        tx_ins=tx_ins,
        tx_outs=tx_outs,
        locktime=data.get('locktime', 0)
    )


def create_success_response(is_valid: bool, tx: Tx) -> Dict[str, Any]:
    """
    Tạo response JSON cho trường hợp thành công.
    
    Args:
        is_valid: Kết quả xác thực
        tx: Transaction đã được xác thực
        
    Returns:
        Dictionary chứa kết quả và TXID
    """
    return {
        'success': True,
        'valid': is_valid,
        'txid': tx.id()
    }


def create_error_response(error_message: str) -> Dict[str, Any]:
    """
    Tạo response JSON cho trường hợp lỗi.
    
    Args:
        error_message: Mô tả lỗi
        
    Returns:
        Dictionary chứa thông tin lỗi
    """
    return {
        'success': False,
        'error': error_message
    }


# =============================================================================
# API ENDPOINTS
# =============================================================================

@tx_api.route('/verify', methods=['POST'])
def verify_transaction():
    """
    Xác thực tính hợp lệ của một transaction.
    
    Endpoint này kiểm tra:
    1. Cấu trúc transaction có đúng format không
    2. Tất cả inputs có tồn tại trong UTXO set không
    3. Tổng inputs >= tổng outputs (fee >= 0)
    4. Signatures có hợp lệ không
    
    Request JSON:
        {
            "version": 1,
            "tx_ins": [...],
            "tx_outs": [...],
            "locktime": 0,
            "utxo_set": {
                "prev_tx_hash": {
                    "0": {"amount": 1000000, "script_pubkey": [...]}
                }
            }
        }
        
    Response JSON:
        Success: {"success": true, "valid": true/false, "txid": "..."}
        Error: {"success": false, "error": "error message"}
        
    Returns:
        tuple: (JSON response, HTTP status code)
    """
    try:
        # Lấy dữ liệu từ request
        data = request.get_json()
        
        if not data:
            return jsonify(create_error_response("No JSON data provided")), 400
        
        # Parse transaction từ JSON
        tx = parse_transaction_from_json(data)
        
        # Lấy UTXO set từ request
        utxo_set = data.get('utxo_set', {})
        
        # Xác thực transaction
        is_valid = TransactionVerifier.verify_transaction(tx, utxo_set)
        
        return jsonify(create_success_response(is_valid, tx))
        
    except KeyError as e:
        # Thiếu field bắt buộc
        return jsonify(create_error_response(f"Missing required field: {e}")), 400
        
    except ValueError as e:
        # Giá trị không hợp lệ
        return jsonify(create_error_response(f"Invalid value: {e}")), 400
        
    except Exception as e:
        # Lỗi không xác định
        return jsonify(create_error_response(str(e))), 400


@tx_api.route('/verify/coinbase', methods=['POST'])
def verify_coinbase():
    """
    Xác thực tính hợp lệ của một coinbase transaction.
    
    Coinbase transaction là transaction đặc biệt:
    - Là transaction đầu tiên trong mỗi block
    - Tạo ra Bitcoin mới (block reward + transaction fees)
    - Input có prev_tx = zeros và prev_index = 0xffffffff
    
    Request JSON:
        {
            "version": 1,
            "tx_ins": [
                {
                    "prev_tx": "0000...0000" (64 zeros),
                    "prev_index": 4294967295,
                    "script_sig": [block_height, ...],
                    "sequence": 4294967295
                }
            ],
            "tx_outs": [
                {
                    "amount": 5000000000,  // 50 BTC block reward
                    "script_pubkey": ["OP_DUP", ...]
                }
            ],
            "locktime": 0,
            "block_height": 1
        }
        
    Response JSON:
        Success: {"success": true, "valid": true/false, "txid": "..."}
        Error: {"success": false, "error": "error message"}
        
    Returns:
        tuple: (JSON response, HTTP status code)
    """
    try:
        # Lấy dữ liệu từ request
        data = request.get_json()
        
        if not data:
            return jsonify(create_error_response("No JSON data provided")), 400
        
        # Parse transaction từ JSON (dùng chung hàm helper)
        tx = parse_transaction_from_json(data)
        
        # Lấy block height từ request
        block_height = data.get('block_height', 0)
        
        # Xác thực coinbase transaction
        is_valid = TransactionVerifier.verify_coinbase(tx, block_height)
        
        return jsonify(create_success_response(is_valid, tx))
        
    except KeyError as e:
        # Thiếu field bắt buộc
        return jsonify(create_error_response(f"Missing required field: {e}")), 400
        
    except ValueError as e:
        # Giá trị không hợp lệ
        return jsonify(create_error_response(f"Invalid value: {e}")), 400
        
    except Exception as e:
        # Lỗi không xác định
        return jsonify(create_error_response(str(e))), 400


# =============================================================================
# ADDITIONAL ENDPOINTS (có thể mở rộng)
# =============================================================================

@tx_api.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Dùng để kiểm tra API có hoạt động không.
    
    Returns:
        JSON: {"status": "ok"}
    """
    return jsonify({'status': 'ok'})
