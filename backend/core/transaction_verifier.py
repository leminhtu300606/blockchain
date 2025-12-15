"""
Transaction verification module for the blockchain.
Handles validation of transactions including signature verification and input/output validation.
"""
import hashlib
from typing import List, Dict, Any, Optional
from ecdsa import VerifyingKey, SECP256k1, BadSignatureError
from .Tx import Tx, TxIn, TxOut, Script

class TransactionVerifier:
    """Handles verification of transactions in the blockchain."""
    
    @staticmethod
    def verify_transaction(tx: Tx, utxo_set: Dict[str, Dict[int, Dict[str, Any]]]) -> bool:
        """
        Verify a transaction's validity.
        
        Args:
            tx: The transaction to verify
            utxo_set: The current UTXO set (unspent transaction outputs)
            
        Returns:
            bool: True if transaction is valid, False otherwise
        """
        # 1. Check basic structure
        if not tx.tx_ins or (not tx.is_coinbase() and not tx.tx_outs):
            return False
            
        # 2. Verify the transaction's signature(s)
        if not tx.is_coinbase():
            for i, tx_in in enumerate(tx.tx_ins):
                if not TransactionVerifier.verify_input(tx, i, utxo_set):
                    return False
        
        # 3. Check that the sum of inputs >= sum of outputs
        if not tx.is_coinbase():
            input_sum = 0
            output_sum = sum(tx_out.amount for tx_out in tx.tx_outs)
            
            for tx_in in tx.tx_ins:
                prev_tx_id = tx_in.prev_tx
                prev_out_index = tx_in.prev_index
                
                # Skip if input is not in UTXO set
                if prev_tx_id not in utxo_set or prev_out_index not in utxo_set[prev_tx_id]:
                    return False
                    
                prev_tx_out = utxo_set[prev_tx_id][prev_out_index]
                input_sum += prev_tx_out['amount']
            
            if input_sum < output_sum:
                return False
        
        return True
    
    @staticmethod
    def verify_input(tx: Tx, input_index: int, utxo_set: Dict[str, Dict[int, Dict[str, Any]]]) -> bool:
        """
        Verify a single transaction input.
        
        Args:
            tx: The transaction containing the input
            input_index: Index of the input in the transaction
            utxo_set: The current UTXO set
            
        Returns:
            bool: True if input is valid, False otherwise
        """
        tx_in = tx.tx_ins[input_index]
        prev_tx_id = tx_in.prev_tx
        prev_out_index = tx_in.prev_index
        
        # Find the previous transaction output being spent
        if prev_tx_id not in utxo_set or prev_out_index not in utxo_set[prev_tx_id]:
            return False
            
        prev_tx_out = utxo_set[prev_tx_id][prev_out_index]
        
        # Verify the script (simplified - in a real implementation, you'd execute the script)
        script_pubkey = prev_tx_out.get('script_pubkey', '')
        script_sig = tx_in.script_sig.cmds if hasattr(tx_in.script_sig, 'cmds') else []
        
        # In a real implementation, you would execute the script here
        # This is a simplified check that just verifies the format
        if not script_pubkey or not script_sig:
            return False
            
        # Verify the signature (simplified - in a real implementation, you'd use proper ECDSA verification)
        try:
            # This is a placeholder for actual signature verification
            # In a real implementation, you would:
            # 1. Reconstruct the signed message (transaction data)
            # 2. Extract the public key from script_sig or script_pubkey
            # 3. Verify the signature against the public key and message
            return True
        except (ValueError, BadSignatureError):
            return False
    
    @staticmethod
    def verify_coinbase(tx: Tx, block_height: int) -> bool:
        """
        Verify a coinbase transaction.
        
        Args:
            tx: The coinbase transaction to verify
            block_height: The height of the block containing this transaction
            
        Returns:
            bool: True if coinbase is valid, False otherwise
        """
        if not tx.is_coinbase():
            return False
            
        # Coinbase should have exactly one input and at least one output
        if len(tx.tx_ins) != 1 or not tx.tx_outs:
            return False
            
        # The first (and only) input should have a special coinbase script
        coinbase_script = tx.tx_ins[0].script_sig
        if not coinbase_script or not hasattr(coinbase_script, 'cmds') or not coinbase_script.cmds:
            return False
            
        # In a real implementation, you would also check:
        # 1. The block reward amount is correct for the current block height
        # 2. The coinbase script contains the block height in a specific format
        
        return True
