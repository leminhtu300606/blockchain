"""
Send BTC Module - Tạo và gửi Bitcoin Transaction

Module này cung cấp các class và functions để:
- Tạo transaction từ UTXOs
- Ký transaction với private key
- Gửi transaction đến network

Classes:
- UTXO: Đại diện cho Unspent Transaction Output
- TxInput: Transaction input
- TxOutput: Transaction output
- Transaction: Complete transaction với signing

Functions:
- create_transaction(): Tạo và ký transaction
- send_transaction(): Gửi transaction đến node
"""
import hashlib
import binascii
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_der


# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_FEE = 1000              # 1000 satoshis default fee
DEFAULT_SEQUENCE = 0xffffffff   # Sequence number (không có RBF)
SIGHASH_ALL = 1                 # Signature hash type


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def encode_varint(n: int) -> bytes:
    """
    Mã hóa số nguyên thành Variable Length Integer.
    
    Format Bitcoin VarInt:
    - 0-252: 1 byte
    - 253-65535: 0xfd + 2 bytes
    - 65536-4294967295: 0xfe + 4 bytes
    - Lớn hơn: 0xff + 8 bytes
    """
    if n < 0xfd:
        return n.to_bytes(1, 'little')
    elif n <= 0xffff:
        return b'\xfd' + n.to_bytes(2, 'little')
    elif n <= 0xffffffff:
        return b'\xfe' + n.to_bytes(4, 'little')
    else:
        return b'\xff' + n.to_bytes(8, 'little')


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class UTXO:
    """
    Unspent Transaction Output - Output chưa được chi tiêu.
    
    UTXO là "tiền" bạn có thể spend trong Bitcoin.
    Mỗi UTXO được định danh bởi (txid, vout).
    
    Attributes:
        txid: Transaction ID nơi UTXO được tạo
        vout: Output index trong transaction
        amount: Số satoshis
        script_pubkey: Locking script (hex)
        address: Địa chỉ sở hữu UTXO
    """
    txid: str
    vout: int
    amount: int
    script_pubkey: str
    address: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'txid': self.txid,
            'vout': self.vout,
            'amount': self.amount,
            'scriptPubKey': self.script_pubkey,
            'address': self.address
        }


@dataclass
class TxInput:
    """
    Transaction Input - Tham chiếu đến UTXO được spend.
    
    Attributes:
        txid: Previous transaction ID
        vout: Previous output index
        script_sig: Unlocking script (signature + pubkey)
        sequence: Sequence number (cho RBF, timelocks)
    """
    txid: str
    vout: int
    script_sig: str = ""
    sequence: int = DEFAULT_SEQUENCE
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'txid': self.txid,
            'vout': self.vout,
            'scriptSig': self.script_sig,
            'sequence': self.sequence
        }


@dataclass
class TxOutput:
    """
    Transaction Output - Định nghĩa recipient và amount.
    
    Attributes:
        address: Địa chỉ nhận (sẽ được convert thành script)
        amount: Số satoshis
    """
    address: str
    amount: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'address': self.address,
            'amount': self.amount
        }


# =============================================================================
# TRANSACTION CLASS
# =============================================================================

class Transaction:
    """
    Bitcoin Transaction - Hoàn chỉnh với signing.
    
    Workflow:
    1. Tạo Transaction()
    2. add_input() cho mỗi UTXO
    3. add_output() cho mỗi recipient
    4. sign_input() cho mỗi input
    5. to_hex() để broadcast
    
    Attributes:
        version: Transaction version (1 hoặc 2)
        inputs: List of TxInput
        outputs: List of TxOutput
        locktime: Thời điểm sớm nhất có thể confirm
        txid: Transaction ID (sau khi serialize)
    """
    
    def __init__(self, version: int = 1, locktime: int = 0):
        """
        Khởi tạo Transaction.
        
        Args:
            version: Transaction version (default: 1)
            locktime: Block height hoặc timestamp (default: 0)
        """
        self.version = version
        self.inputs: List[TxInput] = []
        self.outputs: List[TxOutput] = []
        self.locktime = locktime
        self.txid: Optional[str] = None
    
    # =========================================================================
    # INPUT/OUTPUT MANAGEMENT
    # =========================================================================
    
    def add_input(self, tx_input: TxInput) -> None:
        """Thêm input vào transaction."""
        self.inputs.append(tx_input)
    
    def add_output(self, tx_output: TxOutput) -> None:
        """Thêm output vào transaction."""
        self.outputs.append(tx_output)
    
    # =========================================================================
    # SIGNING
    # =========================================================================
    
    def sign_input(
        self, 
        input_index: int, 
        private_key: str, 
        utxo_script_pubkey: str
    ) -> str:
        """
        Ký một input với private key.
        
        Process:
        1. Tạo bản sao transaction để ký
        2. Thay scriptSig của input đang ký bằng scriptPubKey của UTXO
        3. Hash transaction (double SHA-256)
        4. Ký hash với ECDSA
        5. Append SIGHASH_ALL byte
        
        Args:
            input_index: Index của input cần ký
            private_key: Private key (hex string)
            utxo_script_pubkey: ScriptPubKey của UTXO được spend
            
        Returns:
            str: Signature (DER format + SIGHASH byte) as hex
        """
        # Load private key
        sk = SigningKey.from_string(
            bytes.fromhex(private_key), 
            curve=SECP256k1
        )
        
        # Tính signature hash
        sighash = self._calculate_sighash(input_index, utxo_script_pubkey)
        
        # Ký deterministically
        signature = sk.sign_digest_deterministic(
            sighash,
            sigencode=sigencode_der,
            hashfunc=hashlib.sha256
        )
        
        # Append SIGHASH_ALL
        signature += bytes([SIGHASH_ALL])
        
        return binascii.hexlify(signature).decode('ascii')
    
    def _calculate_sighash(
        self, 
        input_index: int, 
        script_pubkey: str
    ) -> bytes:
        """
        Tính hash để ký cho một input.
        
        Simplified SIGHASH_ALL:
        1. Copy transaction
        2. Empty tất cả scriptSig
        3. Put scriptPubKey vào input đang ký
        4. Append SIGHASH type
        5. Double SHA-256
        """
        # Tạo copy để ký
        tx_copy = Transaction(version=self.version, locktime=self.locktime)
        
        for i, inp in enumerate(self.inputs):
            # ScriptSig = scriptPubKey cho input đang ký, empty cho các input khác
            script = script_pubkey if i == input_index else ""
            tx_copy.add_input(TxInput(
                txid=inp.txid,
                vout=inp.vout,
                script_sig=script,
                sequence=inp.sequence
            ))
        
        for out in self.outputs:
            tx_copy.add_output(out)
        
        # Serialize + SIGHASH type
        serialized = tx_copy.serialize()
        serialized += SIGHASH_ALL.to_bytes(4, 'little')
        
        # Double SHA-256
        return hashlib.sha256(hashlib.sha256(serialized).digest()).digest()
    
    # =========================================================================
    # SERIALIZATION
    # =========================================================================
    
    def serialize(self) -> bytes:
        """
        Serialize transaction thành bytes.
        
        Format:
        - Version (4 bytes)
        - Input count (VarInt)
        - Inputs
        - Output count (VarInt)
        - Outputs
        - Locktime (4 bytes)
        """
        result = bytearray()
        
        # Version
        result.extend(self.version.to_bytes(4, 'little'))
        
        # Input count
        result.extend(encode_varint(len(self.inputs)))
        
        # Inputs
        for inp in self.inputs:
            # Previous tx hash (reversed)
            result.extend(bytes.fromhex(inp.txid)[::-1])
            # Previous output index
            result.extend(inp.vout.to_bytes(4, 'little'))
            # ScriptSig
            script = bytes.fromhex(inp.script_sig) if inp.script_sig else b''
            result.extend(encode_varint(len(script)))
            result.extend(script)
            # Sequence
            result.extend(inp.sequence.to_bytes(4, 'little'))
        
        # Output count
        result.extend(encode_varint(len(self.outputs)))
        
        # Outputs
        for out in self.outputs:
            # Amount
            result.extend(out.amount.to_bytes(8, 'little'))
            # ScriptPubKey (simplified P2PKH)
            script = f"76a914{out.address}88ac"
            script_bytes = bytes.fromhex(script)
            result.extend(encode_varint(len(script_bytes)))
            result.extend(script_bytes)
        
        # Locktime
        result.extend(self.locktime.to_bytes(4, 'little'))
        
        return bytes(result)
    
    def calculate_fee(self, utxos: List[UTXO]) -> int:
        """
        Tính transaction fee.
        
        Fee = sum(inputs) - sum(outputs)
        """
        input_sum = sum(utxo.amount for utxo in utxos)
        output_sum = sum(out.amount for out in self.outputs)
        return input_sum - output_sum
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'txid': self.txid,
            'version': self.version,
            'inputs': [inp.to_dict() for inp in self.inputs],
            'outputs': [out.to_dict() for out in self.outputs],
            'locktime': self.locktime
        }
    
    def to_hex(self) -> str:
        """Serialize thành hex string để broadcast."""
        return self.serialize().hex()


# =============================================================================
# TRANSACTION CREATION FUNCTIONS
# =============================================================================

def create_transaction(
    inputs: List[UTXO],
    outputs: List[TxOutput],
    private_key: str,
    fee: int = DEFAULT_FEE
) -> Transaction:
    """
    Tạo và ký transaction.
    
    Workflow:
    1. Tạo Transaction object
    2. Thêm inputs từ UTXOs
    3. Thêm outputs
    4. Ký từng input
    5. Tính TXID
    
    Args:
        inputs: List of UTXOs to spend
        outputs: List of outputs to create
        private_key: Private key (hex) để ký
        fee: Transaction fee (satoshis)
        
    Returns:
        Transaction: Signed transaction
    """
    tx = Transaction()
    
    # Add inputs
    for utxo in inputs:
        tx.add_input(TxInput(txid=utxo.txid, vout=utxo.vout))
    
    # Add outputs
    for output in outputs:
        tx.add_output(output)
    
    # Sign each input
    for i, utxo in enumerate(inputs):
        signature = tx.sign_input(i, private_key, utxo.script_pubkey)
        tx.inputs[i].script_sig = signature
    
    # Calculate TXID
    tx.txid = hashlib.sha256(
        hashlib.sha256(tx.serialize()).digest()
    ).hexdigest()
    
    logger.info(f"Created transaction: {tx.txid[:16]}...")
    return tx


def send_transaction(
    tx_hex: str, 
    node_url: str = "http://localhost:8332"
) -> dict:
    """
    Gửi transaction đến Bitcoin node.
    
    Note: Đây là mock implementation. 
    Production cần kết nối thực đến Bitcoin node RPC.
    
    Args:
        tx_hex: Raw transaction hex
        node_url: URL của Bitcoin node
        
    Returns:
        dict: Response từ node
    """
    # Mock response
    txid = hashlib.sha256(bytes.fromhex(tx_hex)).hexdigest()
    
    logger.info(f"Transaction sent (simulated): {txid[:16]}...")
    
    return {
        'txid': txid,
        'success': True,
        'message': 'Transaction sent successfully (simulated)'
    }