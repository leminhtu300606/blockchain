"""
Transaction utilities for signing and verifying transactions in debug mode.
This module provides helper functions for creating, signing, and verifying transactions.
"""
import hashlib
import ecdsa
from typing import List, Tuple, Dict, Any, Optional
import sys
import os
import logging

# Add the parent directory to the path to allow relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.Tx import Tx, TxIn, TxOut, Script

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Use the secp256k1 curve (same as Bitcoin)
CURVE = ecdsa.SECP256k1

class DebugTransactionError(Exception):
    """Custom exception for transaction debugging"""
    pass

def generate_keypair() -> Tuple[ecdsa.SigningKey, ecdsa.VerifyingKey]:
    """
    Generate a new ECDSA keypair for testing.
    
    Returns:
        tuple: (private_key, public_key) as ecdsa.SigningKey and ecdsa.VerifyingKey objects
    """
    private_key = ecdsa.SigningKey.generate(curve=CURVE)
    public_key = private_key.get_verifying_key()
    return private_key, public_key

def create_p2pkh_script(pubkey_hash: bytes) -> Script:
    """
    Create a Pay-to-Public-Key-Hash (P2PKH) script.
    
    Args:
        pubkey_hash: The RIPEMD160(SHA256(public_key)) hash
        
    Returns:
        Script: A P2PKH script
    """
    return Script([
        'OP_DUP',
        'OP_HASH160',
        pubkey_hash.hex(),
        'OP_EQUALVERIFY',
        'OP_CHECKSIG'
    ])

def sign_transaction(transaction: Tx, input_index: int, private_key: ecdsa.SigningKey, 
                   prev_tx_script_pubkey: Script, sighash_type: int = 0x01) -> bytes:
    """
    Sign a transaction input.
    
    Args:
        transaction: The transaction to sign
        input_index: Index of the input to sign
        private_key: The private key to sign with
        prev_tx_script_pubkey: The scriptPubKey of the previous transaction output
        sighash_type: Signature hash type (default: SIGHASH_ALL)
        
    Returns:
        bytes: The DER-encoded signature
    """
    # Create a copy of the transaction to sign
    tx_copy = Tx(
        version=transaction.version,
        tx_ins=[],
        tx_outs=transaction.tx_outs,
        locktime=transaction.locktime
    )
    
    # Add inputs with empty script_sigs
    for i, tx_in in enumerate(transaction.tx_ins):
        if i == input_index:
            # Replace script_sig with the previous script_pubkey for the input being signed
            tx_copy.tx_ins.append(TxIn(
                prev_tx=tx_in.prev_tx,
                prev_index=tx_in.prev_index,
                script_sig=prev_tx_script_pubkey,
                sequence=tx_in.sequence
            ))
        else:
            # Empty script_sig for other inputs
            tx_copy.tx_ins.append(TxIn(
                prev_tx=tx_in.prev_tx,
                prev_index=tx_in.prev_index,
                script_sig=Script(),
                sequence=tx_in.sequence
            ))
    
    # Add sighash type to the end of the signature
    sighash = int_to_bytes(sighash_type, 4)
    
    # Serialize and hash the transaction
    tx_serialized = tx_copy.serialize() + sighash
    tx_hash = hashlib.sha256(hashlib.sha256(tx_serialized).digest()).digest()
    
    # Sign the hash
    signature = private_key.sign_digest(tx_hash, sigencode=ecdsa.util.sigencode_der_canonize)
    
    # Append sighash type to signature
    return signature + bytes([sighash_type])

def verify_transaction(tx: Tx, utxo_set: Dict[str, Dict[int, Dict[str, Any]]]) -> bool:
    """
    Verify a transaction's signatures.
    
    Args:
        transaction: The transaction to verify
        utxo_set: The UTXO set to check against
        
    Returns:
        bool: True if all signatures are valid, False otherwise
    """
    for i, tx_in in enumerate(tx.tx_ins):
        # Skip coinbase transactions
        if tx.is_coinbase():
            continue
            
        # Get the previous transaction output
        prev_tx_id = tx_in.prev_tx
        prev_out_index = tx_in.prev_index
        
        if prev_tx_id not in utxo_set or prev_out_index not in utxo_set[prev_tx_id]:
            logger.error(f"Input {i}: Could not find UTXO {prev_tx_id}:{prev_out_index}")
            return False
            
        prev_tx_out = utxo_set[prev_tx_id][prev_out_index]
        script_pubkey = prev_tx_out.get('script_pubkey')
        
        if not script_pubkey:
            logger.error(f"Input {i}: No script_pubkey found for UTXO {prev_tx_id}:{prev_out_index}")
            return False
            
        # Convert script_pubkey to Script object if it's a list
        if isinstance(script_pubkey, list):
            script_pubkey = Script(script_pubkey)
            
        # For P2PKH scripts, extract the public key hash
        if (len(script_pubkey.cmds) == 5 and 
            script_pubkey.cmds[0] == 'OP_DUP' and
            script_pubkey.cmds[1] == 'OP_HASH160' and
            script_pubkey.cmds[3] == 'OP_EQUALVERIFY' and
            script_pubkey.cmds[4] == 'OP_CHECKSIG'):
            
            pubkey_hash = bytes.fromhex(script_pubkey.cmds[2])
            
            # Get the signature and public key from script_sig
            if len(tx_in.script_sig.cmds) != 2:
                logger.error(f"Input {i}: Invalid script_sig format")
                return False
                
            signature = tx_in.script_sig.cmds[0]
            pubkey = tx_in.script_sig.cmds[1]
            
            # Verify the public key hash matches
            if hashlib.sha256(bytes.fromhex(pubkey)).digest() != pubkey_hash:
                logger.error(f"Input {i}: Public key hash does not match")
                return False
                
            # Verify the signature
            try:
                vk = ecdsa.VerifyingKey.from_string(
                    bytes.fromhex(pubkey),
                    curve=CURVE
                )
                
                # Create a copy of the transaction for verification
                tx_copy = Tx(
                    version=tx.version,
                    tx_ins=[],
                    tx_outs=tx.tx_outs,
                    locktime=tx.locktime
                )
                
                # Add inputs with empty script_sigs
                for j, tx_in_copy in enumerate(tx.tx_ins):
                    if j == i:
                        # Replace script_sig with the previous script_pubkey
                        tx_copy.tx_ins.append(TxIn(
                            prev_tx=tx_in_copy.prev_tx,
                            prev_index=tx_in_copy.prev_index,
                            script_sig=script_pubkey,
                            sequence=tx_in_copy.sequence
                        ))
                    else:
                        # Empty script_sig for other inputs
                        tx_copy.tx_ins.append(TxIn(
                            prev_tx=tx_in_copy.prev_tx,
                            prev_index=tx_in_copy.prev_index,
                            script_sig=Script(),
                            sequence=tx_in_copy.sequence
                        ))
                
                # Add sighash type to the end of the signature
                sighash_type = signature[-1]
                sighash = int_to_bytes(sighash_type, 4)
                
                # Serialize and hash the transaction
                tx_serialized = tx_copy.serialize() + sighash
                tx_hash = hashlib.sha256(hashlib.sha256(tx_serialized).digest()).digest()
                
                # Verify the signature
                if not vk.verify_digest(signature[:-1], tx_hash, sigdecode=ecdsa.util.sigdecode_der):
                    logger.error(f"Input {i}: Invalid signature")
                    return False
                    
            except Exception as e:
                logger.error(f"Input {i}: Error verifying signature: {str(e)}")
                return False
                
    return True

def create_signed_transaction(inputs: List[Dict], outputs: List[Dict], 
                            private_key: ecdsa.SigningKey, utxo_set: Dict[str, Dict[int, Dict]]) -> Tx:
    """
    Create and sign a new transaction.
    
    Args:
        inputs: List of input dictionaries with 'txid', 'vout', and 'script_pubkey'
        outputs: List of output dictionaries with 'amount' and 'script_pubkey'
        private_key: The private key to sign with
        utxo_set: The UTXO set to get previous transaction data from
        
    Returns:
        Tx: The signed transaction
    """
    # Create transaction inputs
    tx_ins = []
    for input_data in inputs:
        tx_in = TxIn(
            prev_tx=input_data['txid'],
            prev_index=input_data['vout'],
            script_sig=Script()  # Will be filled in during signing
        )
        tx_ins.append(tx_in)
    
    # Create transaction outputs
    tx_outs = []
    for output in outputs:
        tx_out = TxOut(
            amount=output['amount'],
            script_pubkey=output['script_pubkey']
        )
        tx_outs.append(tx_out)
    
    # Create the transaction
    tx = Tx(
        version=1,
        tx_ins=tx_ins,
        tx_outs=tx_outs,
        locktime=0
    )
    
    # Sign each input
    for i, tx_in in enumerate(tx.tx_ins):
        # Get the previous transaction output
        prev_tx_id = tx_in.prev_tx
        prev_out_index = tx_in.prev_index
        
        if prev_tx_id not in utxo_set or prev_out_index not in utxo_set[prev_tx_id]:
            raise DebugTransactionError(f"Could not find UTXO {prev_tx_id}:{prev_out_index}")
            
        prev_tx_out = utxo_set[prev_tx_id][prev_out_index]
        script_pubkey = prev_tx_out.get('script_pubkey')
        
        if not script_pubkey:
            raise DebugTransactionError(f"No script_pubkey found for UTXO {prev_tx_id}:{prev_out_index}")
        
        # Convert script_pubkey to Script object if it's a list
        if isinstance(script_pubkey, list):
            script_pubkey = Script(script_pubkey)
        
        # Sign the input
        signature = sign_transaction(tx, i, private_key, script_pubkey)
        
        # Get the public key
        public_key = private_key.get_verifying_key().to_string().hex()
        
        # Set the script_sig (signature + public key for P2PKH)
        tx_in.script_sig = Script([signature.hex(), public_key])
    
    return tx

def int_to_bytes(n: int, length: int) -> bytes:
    """Convert an integer to bytes with the specified length"""
    return n.to_bytes(length, byteorder='little')

def debug_print_transaction(tx: Tx, title: str = "Transaction") -> None:
    """Print transaction details for debugging"""
    print(f"\n=== {title} ===")
    print(f"TXID: {tx.id()}")
    print(f"Version: {tx.version}")
    print(f"Locktime: {tx.locktime}")
    
    print("\nInputs:")
    for i, tx_in in enumerate(tx.tx_ins):
        print(f"  Input {i}:")
        print(f"    Previous TX: {tx_in.prev_tx}")
        print(f"    Index: {tx_in.prev_index}")
        print(f"    ScriptSig: {tx_in.script_sig}")
    
    print("\nOutputs:")
    for i, tx_out in enumerate(tx.tx_outs):
        print(f"  Output {i}:")
        print(f"    Amount: {tx_out.amount} satoshis")
        print(f"    ScriptPubKey: {tx_out.script_pubkey}")
    print("=" * 30)
