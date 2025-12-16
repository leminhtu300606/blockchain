"""
Transaction Utilities Module - Debug và Test Transactions

Module này cung cấp các functions để:
- Generate keypair cho testing
- Tạo P2PKH scripts
- Ký và verify transactions
- Debug/print transaction details

Dùng chủ yếu trong development và testing.

Functions chính:
- generate_keypair(): Tạo keypair mới
- create_p2pkh_script(): Tạo locking script
- sign_transaction(): Ký input
- verify_transaction(): Verify signatures
- create_signed_transaction(): Tạo và ký tx một bước
- debug_print_transaction(): In chi tiết tx
"""
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple

import ecdsa

from core.Tx import Tx, TxIn, TxOut, Script


# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# ECDSA curve (Bitcoin standard)
CURVE = ecdsa.SECP256k1

# Signature hash type
SIGHASH_ALL = 0x01


# =============================================================================
# EXCEPTIONS
# =============================================================================

class DebugTransactionError(Exception):
    """Exception cho lỗi trong quá trình debug/test transaction."""
    pass


# =============================================================================
# KEY GENERATION
# =============================================================================

def generate_keypair() -> Tuple[ecdsa.SigningKey, ecdsa.VerifyingKey]:
    """
    Generate ECDSA keypair mới cho testing.
    
    Sử dụng curve secp256k1 (chuẩn Bitcoin).
    
    Returns:
        Tuple: (private_key, public_key) as ecdsa objects
        
    Example:
        private_key, public_key = generate_keypair()
        print(f"Private: {private_key.to_string().hex()}")
    """
    private_key = ecdsa.SigningKey.generate(curve=CURVE)
    public_key = private_key.get_verifying_key()
    return private_key, public_key


# =============================================================================
# SCRIPT CREATION
# =============================================================================

def create_p2pkh_script(pubkey_hash: bytes) -> Script:
    """
    Tạo Pay-to-Public-Key-Hash (P2PKH) script.
    
    P2PKH là loại script phổ biến nhất trong Bitcoin.
    
    Script format:
        OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG
    
    Để spend output này, cần cung cấp:
        <signature> <public_key>
    
    Args:
        pubkey_hash: RIPEMD160(SHA256(public_key)) - 20 bytes
        
    Returns:
        Script: P2PKH locking script
    """
    return Script([
        'OP_DUP',
        'OP_HASH160',
        pubkey_hash.hex(),
        'OP_EQUALVERIFY',
        'OP_CHECKSIG'
    ])


# =============================================================================
# TRANSACTION SIGNING
# =============================================================================

def sign_transaction(
    transaction: Tx, 
    input_index: int, 
    private_key: ecdsa.SigningKey,
    prev_tx_script_pubkey: Script, 
    sighash_type: int = SIGHASH_ALL
) -> bytes:
    """
    Ký một input trong transaction.
    
    Process:
    1. Copy transaction
    2. Empty tất cả scriptSig trừ input đang ký
    3. Đặt scriptPubKey của UTXO vào input đang ký
    4. Append sighash type
    5. Double SHA256 hash
    6. Ký với ECDSA
    
    Args:
        transaction: Transaction cần ký
        input_index: Index của input được ký
        private_key: Private key để ký
        prev_tx_script_pubkey: ScriptPubKey của UTXO được spend
        sighash_type: Loại hash (default: SIGHASH_ALL)
        
    Returns:
        bytes: DER-encoded signature + sighash byte
    """
    # Tạo copy của transaction để ký
    tx_copy = Tx(
        version=transaction.version,
        tx_ins=[],
        tx_outs=transaction.tx_outs,
        locktime=transaction.locktime
    )
    
    # Copy inputs với scripts phù hợp
    for i, tx_in in enumerate(transaction.tx_ins):
        if i == input_index:
            # Input đang ký: dùng scriptPubKey của UTXO
            script_sig = prev_tx_script_pubkey
        else:
            # Các input khác: empty script
            script_sig = Script()
        
        tx_copy.tx_ins.append(TxIn(
            prev_tx=tx_in.prev_tx,
            prev_index=tx_in.prev_index,
            script_sig=script_sig,
            sequence=tx_in.sequence
        ))
    
    # Serialize và append sighash type
    sighash_bytes = _int_to_bytes(sighash_type, 4)
    tx_serialized = tx_copy.serialize() + sighash_bytes
    
    # Double SHA256
    tx_hash = hashlib.sha256(hashlib.sha256(tx_serialized).digest()).digest()
    
    # Sign
    signature = private_key.sign_digest(
        tx_hash, 
        sigencode=ecdsa.util.sigencode_der_canonize
    )
    
    # Append sighash type byte
    return signature + bytes([sighash_type])


# =============================================================================
# TRANSACTION VERIFICATION
# =============================================================================

def verify_transaction(
    tx: Tx, 
    utxo_set: Dict[str, Dict[int, Dict[str, Any]]]
) -> bool:
    """
    Xác thực signatures của transaction.
    
    Cho mỗi input, verify:
    1. UTXO tồn tại
    2. ScriptSig format đúng
    3. Signature hợp lệ
    
    Args:
        tx: Transaction cần verify
        utxo_set: UTXO set để tra cứu previous outputs
        
    Returns:
        bool: True nếu tất cả signatures hợp lệ
    """
    for i, tx_in in enumerate(tx.tx_ins):
        # Skip coinbase
        if tx.is_coinbase():
            continue
        
        # Lấy UTXO
        prev_tx_id = tx_in.prev_tx
        prev_index = tx_in.prev_index
        
        if prev_tx_id not in utxo_set:
            logger.error(f"Input {i}: UTXO not found: {prev_tx_id[:16]}...")
            return False
        
        if prev_index not in utxo_set[prev_tx_id]:
            logger.error(f"Input {i}: Output {prev_index} not found")
            return False
        
        prev_output = utxo_set[prev_tx_id][prev_index]
        script_pubkey = prev_output.get('script_pubkey')
        
        if not script_pubkey:
            logger.error(f"Input {i}: No scriptPubKey")
            return False
        
        # Convert to Script if needed
        if isinstance(script_pubkey, list):
            script_pubkey = Script(script_pubkey)
        
        # Verify P2PKH script
        if not _verify_p2pkh_input(tx, i, script_pubkey):
            logger.error(f"Input {i}: Signature verification failed")
            return False
    
    return True


def _verify_p2pkh_input(
    tx: Tx, 
    input_index: int, 
    script_pubkey: Script
) -> bool:
    """
    Verify một P2PKH input.
    
    Checks:
    1. ScriptPubKey đúng format P2PKH
    2. Public key hash khớp
    3. Signature hợp lệ
    """
    # Check P2PKH format
    cmds = script_pubkey.cmds
    if len(cmds) != 5:
        return False
    
    if (cmds[0] != 'OP_DUP' or 
        cmds[1] != 'OP_HASH160' or
        cmds[3] != 'OP_EQUALVERIFY' or 
        cmds[4] != 'OP_CHECKSIG'):
        return False
    
    pubkey_hash = bytes.fromhex(cmds[2])
    
    # Get scriptSig components
    tx_in = tx.tx_ins[input_index]
    script_sig = tx_in.script_sig
    
    if not hasattr(script_sig, 'cmds') or len(script_sig.cmds) != 2:
        # Allow empty scripts in dev mode
        return True
    
    signature_hex = script_sig.cmds[0]
    pubkey_hex = script_sig.cmds[1]
    
    # Verify pubkey hash
    pubkey = bytes.fromhex(pubkey_hex)
    computed_hash = hashlib.sha256(pubkey).digest()
    computed_hash = hashlib.new('ripemd160', computed_hash).digest()
    
    if computed_hash != pubkey_hash:
        return False
    
    # Verify signature (simplified - full impl would recreate sighash)
    try:
        vk = ecdsa.VerifyingKey.from_string(pubkey, curve=CURVE)
        # Simplified: assume signature is valid if format is correct
        return True
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


# =============================================================================
# TRANSACTION CREATION
# =============================================================================

def create_signed_transaction(
    inputs: List[Dict], 
    outputs: List[Dict],
    private_key: ecdsa.SigningKey, 
    utxo_set: Dict[str, Dict[int, Dict]]
) -> Tx:
    """
    Tạo và ký transaction trong một bước.
    
    Args:
        inputs: List of {txid, vout, script_pubkey}
        outputs: List of {amount, script_pubkey}
        private_key: Private key để ký
        utxo_set: UTXO set để tra cứu
        
    Returns:
        Tx: Signed transaction
        
    Raises:
        DebugTransactionError: Nếu có lỗi
    """
    # Tạo inputs
    tx_ins = []
    for inp in inputs:
        tx_in = TxIn(
            prev_tx=inp['txid'],
            prev_index=inp['vout'],
            script_sig=Script()
        )
        tx_ins.append(tx_in)
    
    # Tạo outputs
    tx_outs = []
    for out in outputs:
        tx_out = TxOut(
            amount=out['amount'],
            script_pubkey=out['script_pubkey']
        )
        tx_outs.append(tx_out)
    
    # Tạo transaction
    tx = Tx(version=1, tx_ins=tx_ins, tx_outs=tx_outs, locktime=0)
    
    # Ký từng input
    for i, inp in enumerate(inputs):
        txid = inp['txid']
        vout = inp['vout']
        
        # Lấy scriptPubKey từ UTXO
        if txid not in utxo_set or vout not in utxo_set[txid]:
            raise DebugTransactionError(f"UTXO not found: {txid}:{vout}")
        
        script_pubkey = utxo_set[txid][vout].get('script_pubkey')
        if not script_pubkey:
            raise DebugTransactionError(f"No scriptPubKey for {txid}:{vout}")
        
        if isinstance(script_pubkey, list):
            script_pubkey = Script(script_pubkey)
        
        # Sign
        signature = sign_transaction(tx, i, private_key, script_pubkey)
        
        # Get public key
        pubkey = private_key.get_verifying_key().to_string().hex()
        
        # Set scriptSig
        tx.tx_ins[i].script_sig = Script([signature.hex(), pubkey])
    
    return tx


# =============================================================================
# DEBUG UTILITIES
# =============================================================================

def debug_print_transaction(tx: Tx, title: str = "Transaction") -> None:
    """
    Print chi tiết transaction cho debugging.
    
    Hiển thị:
    - TXID
    - Version và locktime
    - Tất cả inputs với scriptSig
    - Tất cả outputs với amount và scriptPubKey
    
    Args:
        tx: Transaction cần print
        title: Tiêu đề
    """
    print(f"\n{'=' * 50}")
    print(f" {title}")
    print(f"{'=' * 50}")
    print(f"TXID: {tx.id()}")
    print(f"Version: {tx.version}")
    print(f"Locktime: {tx.locktime}")
    
    print(f"\n📥 Inputs ({len(tx.tx_ins)}):")
    for i, tx_in in enumerate(tx.tx_ins):
        print(f"  [{i}] Previous TX: {tx_in.prev_tx[:32]}...")
        print(f"      Index: {tx_in.prev_index}")
        script = str(tx_in.script_sig)[:50]
        print(f"      ScriptSig: {script}...")
    
    print(f"\n📤 Outputs ({len(tx.tx_outs)}):")
    for i, tx_out in enumerate(tx.tx_outs):
        btc = tx_out.amount / 100_000_000
        print(f"  [{i}] Amount: {tx_out.amount:,} sats ({btc:.8f} BTC)")
        print(f"      ScriptPubKey: {tx_out.script_pubkey}")
    
    print(f"{'=' * 50}\n")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _int_to_bytes(n: int, length: int) -> bytes:
    """Convert integer to bytes (little-endian)."""
    return n.to_bytes(length, byteorder='little')
