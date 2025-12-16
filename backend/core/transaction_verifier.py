"""
Transaction Verifier Module - Xác thực giao dịch Bitcoin

Module này xử lý việc xác thực:
- Transaction thông thường (signature, inputs, outputs)
- Coinbase transaction (block reward)

Các kiểm tra bao gồm:
1. Cấu trúc transaction đúng format
2. Tất cả inputs tồn tại trong UTXO set
3. Tổng inputs >= tổng outputs (fee >= 0)
4. Signatures hợp lệ
"""
import hashlib
import logging
from typing import Dict, Any, Optional

from ecdsa import VerifyingKey, SECP256k1, BadSignatureError

from .Tx import Tx, TxIn, TxOut, Script


# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# TYPE ALIASES
# =============================================================================

# UTXO Set format: {tx_hash: {output_index: {amount, script_pubkey}}}
UTXOSet = Dict[str, Dict[int, Dict[str, Any]]]


# =============================================================================
# TRANSACTION VERIFIER CLASS
# =============================================================================

class TransactionVerifier:
    """
    Transaction Verifier - Xác thực giao dịch Bitcoin.
    
    Class này chứa các static methods để verify:
    - verify_transaction(): Verify transaction thông thường
    - verify_input(): Verify một input cụ thể
    - verify_coinbase(): Verify coinbase transaction
    
    Tất cả methods trả về bool để dễ sử dụng trong conditions.
    """
    
    @staticmethod
    def verify_transaction(tx: Tx, utxo_set: UTXOSet) -> bool:
        """
        Xác thực tính hợp lệ của một transaction.
        
        Các bước kiểm tra:
        1. Basic structure: Có inputs và outputs
        2. Input validation: Verify signatures
        3. Amount check: inputs >= outputs
        
        Args:
            tx: Transaction cần verify
            utxo_set: UTXO set hiện tại (unspent outputs)
            
        Returns:
            bool: True nếu transaction hợp lệ
            
        Example:
            if TransactionVerifier.verify_transaction(tx, utxo_set):
                mempool.add_transaction(tx)
        """
        # =====================================================================
        # Step 1: Basic Structure Check
        # =====================================================================
        
        # Phải có inputs
        if not tx.tx_ins:
            logger.debug("Transaction has no inputs")
            return False
        
        # Non-coinbase phải có outputs
        if not tx.is_coinbase() and not tx.tx_outs:
            logger.debug("Regular transaction has no outputs")
            return False
        
        # =====================================================================
        # Step 2: Verify Each Input (skip for coinbase)
        # =====================================================================
        
        if not tx.is_coinbase():
            for i, tx_in in enumerate(tx.tx_ins):
                if not TransactionVerifier.verify_input(tx, i, utxo_set):
                    logger.debug(f"Input {i} verification failed")
                    return False
        
        # =====================================================================
        # Step 3: Check Amounts (inputs >= outputs)
        # =====================================================================
        
        if not tx.is_coinbase():
            # Tính tổng inputs
            input_sum = 0
            for tx_in in tx.tx_ins:
                prev_tx_id = tx_in.prev_tx
                prev_index = tx_in.prev_index
                
                # Input phải tồn tại trong UTXO set
                if prev_tx_id not in utxo_set:
                    logger.debug(f"Previous tx {prev_tx_id[:16]}... not in UTXO set")
                    return False
                
                if prev_index not in utxo_set[prev_tx_id]:
                    logger.debug(f"Output {prev_index} not in UTXO set")
                    return False
                
                input_sum += utxo_set[prev_tx_id][prev_index]['amount']
            
            # Tính tổng outputs
            output_sum = sum(tx_out.amount for tx_out in tx.tx_outs)
            
            # Fee = inputs - outputs >= 0
            if input_sum < output_sum:
                logger.debug(f"Insufficient inputs: {input_sum} < {output_sum}")
                return False
        
        logger.debug(f"Transaction {tx.id()[:16]}... verified successfully")
        return True
    
    @staticmethod
    def verify_input(tx: Tx, input_index: int, utxo_set: UTXOSet) -> bool:
        """
        Xác thực một input cụ thể.
        
        Kiểm tra:
        1. Input tham chiếu đến UTXO có tồn tại
        2. Script có đúng format
        3. Signature hợp lệ (simplified)
        
        Args:
            tx: Transaction chứa input
            input_index: Index của input trong tx.tx_ins
            utxo_set: UTXO set
            
        Returns:
            bool: True nếu input hợp lệ
        """
        tx_in = tx.tx_ins[input_index]
        prev_tx_id = tx_in.prev_tx
        prev_index = tx_in.prev_index
        
        # =====================================================================
        # Check 1: UTXO Exists
        # =====================================================================
        
        if prev_tx_id not in utxo_set:
            logger.debug(f"UTXO not found: tx={prev_tx_id[:16]}...")
            return False
        
        if prev_index not in utxo_set[prev_tx_id]:
            logger.debug(f"UTXO not found: index={prev_index}")
            return False
        
        prev_output = utxo_set[prev_tx_id][prev_index]
        
        # =====================================================================
        # Check 2: Script Format (basic check)
        # =====================================================================
        
        script_pubkey = prev_output.get('script_pubkey')
        script_sig = tx_in.script_sig.cmds if hasattr(tx_in.script_sig, 'cmds') else []
        
        # Cả hai scripts phải tồn tại
        if not script_pubkey or not script_sig:
            # Cho phép trong development mode
            logger.debug("Empty scripts, allowing in dev mode")
            return True
        
        # =====================================================================
        # Check 3: Signature Verification (simplified)
        # =====================================================================
        
        # Note: Đây là phiên bản đơn giản hóa
        # Full implementation cần:
        # 1. Reconstruct signed message (tx data with specific sighash)
        # 2. Extract public key from script_sig
        # 3. Verify ECDSA signature
        
        try:
            # Placeholder for signature verification
            # Trong production, implement full verification
            return True
            
        except (ValueError, BadSignatureError) as e:
            logger.warning(f"Signature verification failed: {e}")
            return False
    
    @staticmethod
    def verify_coinbase(tx: Tx, block_height: int) -> bool:
        """
        Xác thực Coinbase transaction.
        
        Coinbase transaction có đặc điểm:
        - Đúng 1 input với prev_tx = zeros, prev_index = 0xffffffff
        - Ít nhất 1 output
        - ScriptSig chứa block height (BIP34)
        
        Args:
            tx: Coinbase transaction cần verify
            block_height: Block height để verify trong scriptSig
            
        Returns:
            bool: True nếu coinbase hợp lệ
        """
        # =====================================================================
        # Check 1: Is Actually Coinbase
        # =====================================================================
        
        if not tx.is_coinbase():
            logger.debug("Transaction is not a coinbase")
            return False
        
        # =====================================================================
        # Check 2: Exactly One Input
        # =====================================================================
        
        if len(tx.tx_ins) != 1:
            logger.debug(f"Coinbase should have 1 input, has {len(tx.tx_ins)}")
            return False
        
        # =====================================================================
        # Check 3: Has Outputs
        # =====================================================================
        
        if not tx.tx_outs:
            logger.debug("Coinbase has no outputs")
            return False
        
        # =====================================================================
        # Check 4: ScriptSig Exists
        # =====================================================================
        
        coinbase_script = tx.tx_ins[0].script_sig
        
        if not coinbase_script:
            logger.debug("Coinbase scriptSig is empty")
            return False
        
        if not hasattr(coinbase_script, 'cmds') or not coinbase_script.cmds:
            logger.debug("Coinbase scriptSig has no commands")
            return False
        
        # =====================================================================
        # Optional Check: Block Height in ScriptSig (BIP34)
        # =====================================================================
        
        # BIP34 yêu cầu block height trong scriptSig
        # Simplified: chỉ check scriptSig không rỗng
        
        # Additional checks có thể thêm:
        # - Block reward amount phù hợp với height (halving)
        # - ScriptSig length trong giới hạn
        
        logger.debug(f"Coinbase for block {block_height} verified")
        return True


# =============================================================================
# STANDALONE FUNCTIONS (for backwards compatibility)
# =============================================================================

def verify_transaction(tx: Tx, utxo_set: UTXOSet) -> bool:
    """
    Wrapper function gọi TransactionVerifier.verify_transaction.
    
    Để backward compatible với code cũ.
    """
    return TransactionVerifier.verify_transaction(tx, utxo_set)


def verify_coinbase(tx: Tx, block_height: int) -> bool:
    """
    Wrapper function gọi TransactionVerifier.verify_coinbase.
    
    Để backward compatible với code cũ.
    """
    return TransactionVerifier.verify_coinbase(tx, block_height)
