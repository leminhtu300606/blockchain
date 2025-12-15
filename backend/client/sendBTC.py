import hashlib
import json
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_der
import binascii

# Constants
DEFAULT_FEE = 1000  # 1000 satoshis as default fee
DEFAULT_SEQUENCE = 0xffffffff
SIGHASH_ALL = 1

@dataclass
class UTXO:
    """Unspent Transaction Output"""
    txid: str           # Transaction ID where this UTXO was created
    vout: int           # Output index in the transaction
    amount: int         # Amount in satoshis
    script_pubkey: str  # Locking script in hex
    address: str        # Address that can spend this UTXO
    
    def to_dict(self) -> dict:
        return {
            'txid': self.txid,
            'vout': self.vout,
            'amount': self.amount,
            'scriptPubKey': self.script_pubkey,
            'address': self.address
        }

@dataclass
class TxInput:
    """Transaction Input"""
    txid: str           # Previous transaction ID
    vout: int           # Previous output index
    script_sig: str = ""  # Script that solves the scriptPubKey
    sequence: int = DEFAULT_SEQUENCE
    
    def to_dict(self) -> dict:
        return {
            'txid': self.txid,
            'vout': self.vout,
            'scriptSig': self.script_sig,
            'sequence': self.sequence
        }

@dataclass
class TxOutput:
    """Transaction Output"""
    address: str  # Recipient address
    amount: int   # Amount in satoshis
    
    def to_dict(self) -> dict:
        return {
            'address': self.address,
            'amount': self.amount
        }

class Transaction:
    """Bitcoin Transaction"""
    def __init__(self, version: int = 1, locktime: int = 0):
        self.version = version
        self.inputs: List[TxInput] = []
        self.outputs: List[TxOutput] = []
        self.locktime = locktime
        self.txid: Optional[str] = None
        self.hash: Optional[str] = None
    
    def add_input(self, tx_input: TxInput) -> None:
        """Add an input to the transaction"""
        self.inputs.append(tx_input)
    
    def add_output(self, tx_output: TxOutput) -> None:
        """Add an output to the transaction"""
        self.outputs.append(tx_output)
    
    def sign_input(self, input_index: int, private_key: str, utxo_script_pubkey: str) -> str:
        """Sign a transaction input with the provided private key"""
        # Create a signature for the input at the given index
        # This is a simplified version - in a real implementation, you'd need to handle SIGHASH flags properly
        
        # Get the private key in the right format
        sk = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1)
        
        # Create the signature hash
        sighash = self.calculate_signature_hash(input_index, utxo_script_pubkey)
        
        # Sign the hash
        signature = sk.sign_digest_deterministic(
            sighash,
            sigencode=sigencode_der,
            hashfunc=hashlib.sha256
        )
        
        # Add the SIGHASH_ALL byte (0x01)
        signature += bytes([SIGHASH_ALL])
        
        # Convert to hex
        return binascii.hexlify(signature).decode('ascii')
    
    def calculate_signature_hash(self, input_index: int, script_pubkey_hex: str) -> bytes:
        """Calculate the signature hash for a transaction input"""
        # This is a simplified version - a full implementation would need to handle different SIGHASH types
        
        # Create a copy of the transaction with modified scripts
        tx_copy = Transaction(version=self.version, locktime=self.locktime)
        
        # Copy inputs with empty scripts
        for i, tx_in in enumerate(self.inputs):
            script_sig = "" if i != input_index else script_pubkey_hex
            tx_copy.add_input(TxInput(
                txid=tx_in.txid,
                vout=tx_in.vout,
                script_sig=script_sig,
                sequence=tx_in.sequence
            ))
        
        # Copy outputs
        for tx_out in self.outputs:
            tx_copy.add_output(tx_out)
        
        # Serialize and hash the transaction
        serialized = tx_copy.serialize()
        
        # Add SIGHASH_ALL
        serialized += (SIGHASH_ALL).to_bytes(4, 'little')
        
        # Double SHA-256 hash
        return hashlib.sha256(hashlib.sha256(serialized).digest()).digest()
    
    def serialize(self) -> bytes:
        """Serialize the transaction to bytes"""
        result = bytearray()
        
        # Version
        result.extend(self.version.to_bytes(4, 'little'))
        
        # Input count (varint)
        result.extend(self._encode_varint(len(self.inputs)))
        
        # Inputs
        for tx_in in self.inputs:
            # Previous tx hash (little-endian)
            result.extend(bytes.fromhex(tx_in.txid)[::-1])
            # Previous output index
            result.extend(tx_in.vout.to_bytes(4, 'little'))
            # Script length and script
            script_sig = bytes.fromhex(tx_in.script_sig) if tx_in.script_sig else b''
            result.extend(self._encode_varint(len(script_sig)))
            result.extend(script_sig)
            # Sequence
            result.extend(tx_in.sequence.to_bytes(4, 'little'))
        
        # Output count (varint)
        result.extend(self._encode_varint(len(self.outputs)))
        
        # Outputs
        for tx_out in self.outputs:
            # Amount in satoshis (8 bytes, little-endian)
            result.extend(tx_out.amount.to_bytes(8, 'little'))
            # Script length and script (simplified - in reality you'd create proper P2PKH/P2SH scripts)
            script_pubkey = f"76a914{tx_out.address}88ac"  # P2PKH script
            script_bytes = bytes.fromhex(script_pubkey)
            result.extend(self._encode_varint(len(script_bytes)))
            result.extend(script_bytes)
        
        # Locktime
        result.extend(self.locktime.to_bytes(4, 'little'))
        
        return bytes(result)
    
    def calculate_fee(self, utxos: List[UTXO]) -> int:
        """Calculate the transaction fee based on inputs and outputs"""
        input_amount = sum(utxo.amount for utxo in utxos)
        output_amount = sum(tx_out.amount for tx_out in self.outputs)
        return input_amount - output_amount
    
    def to_dict(self) -> dict:
        """Convert transaction to dictionary"""
        return {
            'txid': self.txid,
            'version': self.version,
            'inputs': [tx_in.to_dict() for tx_in in self.inputs],
            'outputs': [tx_out.to_dict() for tx_out in self.outputs],
            'locktime': self.locktime
        }
    
    def to_hex(self) -> str:
        """Convert transaction to hex string"""
        return self.serialize().hex()
    
    @staticmethod
    def _encode_varint(n: int) -> bytes:
        """Encode an integer as a variable length integer (varint)"""
        if n < 0xfd:
            return n.to_bytes(1, 'little')
        elif n <= 0xffff:
            return b'\xfd' + n.to_bytes(2, 'little')
        elif n <= 0xffffffff:
            return b'\xfe' + n.to_bytes(4, 'little')
        else:
            return b'\xff' + n.to_bytes(8, 'little')


def create_transaction(
    inputs: List[UTXO],
    outputs: List[TxOutput],
    private_key: str,
    fee: int = DEFAULT_FEE
) -> Transaction:
    """
    Create a new transaction
    
    Args:
        inputs: List of UTXOs to spend
        outputs: List of outputs to create
        private_key: Private key in hex format to sign the transaction
        fee: Transaction fee in satoshis
        
    Returns:
        Signed transaction
    """
    # Create a new transaction
    tx = Transaction()
    
    # Add inputs
    for utxo in inputs:
        tx_input = TxInput(
            txid=utxo.txid,
            vout=utxo.vout
        )
        tx.add_input(tx_input)
    
    # Add outputs
    for output in outputs:
        tx.add_output(output)
    
    # Sign each input
    for i, utxo in enumerate(inputs):
        # In a real implementation, you'd need to get the scriptPubKey for each UTXO
        script_pubkey = utxo.script_pubkey
        signature = tx.sign_input(i, private_key, script_pubkey)
        
        # Create scriptSig (simplified - in reality this would be a proper script)
        tx.inputs[i].script_sig = signature
    
    # Calculate and set txid
    tx_hex = tx.serialize().hex()
    tx.txid = hashlib.sha256(hashlib.sha256(tx.serialize()).digest()).hexdigest()
    
    return tx

def send_transaction(tx_hex: str, node_url: str = "http://localhost:8332") -> dict:
    """
    Send a raw transaction to the Bitcoin network
    
    Args:
        tx_hex: Raw transaction in hex format
        node_url: URL of the Bitcoin node to send the transaction to
        
    Returns:
        Response from the node
    """
    # This is a placeholder - in a real implementation, you would:
    # 1. Connect to a Bitcoin node via RPC
    # 2. Call the sendrawtransaction RPC method
    # 3. Return the transaction ID
    
    # For now, just return a mock response
    return {
        'txid': hashlib.sha256(bytes.fromhex(tx_hex)).hexdigest(),
        'success': True,
        'message': 'Transaction sent successfully (simulated)'
    }