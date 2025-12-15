import hashlib

class Script:
    """Basic implementation of a Bitcoin script"""
    def __init__(self, cmds=None):
        if cmds is None:
            self.cmds = []
        else:
            self.cmds = cmds
    
    def __repr__(self):
        return f"Script({self.cmds})"
        
    def __str__(self):
        return str(self.cmds)
    
    def __add__(self, other):
        return Script(self.cmds + other.cmds)
    
    def serialize(self):
        # This is a simplified serialization
        return str(self.cmds).encode('utf-8')

class TxIn:
    def __init__(self, prev_tx, prev_index, script_sig=None, sequence=0xffffffff):
        self.prev_tx = prev_tx  # Hash of previous transaction
        self.prev_index = prev_index  # Index of the output in the previous transaction
        
        if script_sig is None:
            self.script_sig = Script()
        else:
            self.script_sig = script_sig
            
        self.sequence = sequence
        
    def to_dict(self):
        """Convert transaction input to dictionary"""
        return {
            'prev_tx': self.prev_tx,
            'prev_index': self.prev_index,
            'script_sig': self.script_sig.cmds if hasattr(self.script_sig, 'cmds') else str(self.script_sig),
            'sequence': self.sequence
        }

class TxOut:
    def __init__(self, amount, script_pubkey):
        self.amount = amount  # Amount in satoshis
        self.script_pubkey = script_pubkey  # Locking script
        
    def to_dict(self):
        """Convert transaction output to dictionary"""
        return {
            'amount': self.amount,
            'script_pubkey': self.script_pubkey.cmds if hasattr(self.script_pubkey, 'cmds') else str(self.script_pubkey)
        }

class Tx:
    def __init__(self, version, tx_ins, tx_outs, locktime):
        self.version = version
        self.tx_ins = tx_ins  # List of TxIn objects
        self.tx_outs = tx_outs  # List of TxOut objects
        self.locktime = locktime

    def id(self):
        """
        Returns the transaction ID (double SHA-256 hash of the serialized transaction).
        The transaction ID is used as a unique identifier for the transaction in the blockchain.
        """
        # Get the serialized transaction data
        tx_serialized = self.serialize()
        # Calculate double SHA-256 hash
        tx_hash = hashlib.sha256(hashlib.sha256(tx_serialized).digest()).digest()
        # Convert to little-endian and then to hex (Bitcoin displays TXIDs in reverse byte order)
        return tx_hash[::-1].hex()
    
    def _encode_varint(self, n):
        """Encode an integer as a variable length integer (varint)"""
        if n < 0xfd:
            return n.to_bytes(1, 'little')
        elif n <= 0xffff:
            return b'\xfd' + n.to_bytes(2, 'little')
        elif n <= 0xffffffff:
            return b'\xfe' + n.to_bytes(4, 'little')
        else:
            return b'\xff' + n.to_bytes(8, 'little')
    
    def serialize(self):
        """
        Serialize the transaction to bytes following Bitcoin's transaction format.
        
        Format (simplified):
        - Version (4 bytes, little-endian)
        - Input count (varint)
        - Inputs
        - Output count (varint)
        - Outputs
        - Locktime (4 bytes, little-endian)
        """
        result = bytearray()
        
        # Version (4 bytes, little-endian)
        result.extend(self.version.to_bytes(4, 'little'))
        
        # Input count (varint)
        result.extend(self._encode_varint(len(self.tx_ins)))
        
        # Serialize inputs
        for tx_in in self.tx_ins:
            # Previous transaction hash (32 bytes, little-endian)
            prev_tx_bytes = bytes.fromhex(tx_in.prev_tx)[::-1]  # Convert hex to bytes and reverse
            result.extend(prev_tx_bytes)
            
            # Previous output index (4 bytes, little-endian)
            result.extend(tx_in.prev_index.to_bytes(4, 'little'))
            
            # ScriptSig (varint + script)
            script_sig = tx_in.script_sig.serialize()
            result.extend(self._encode_varint(len(script_sig)))
            result.extend(script_sig)
            
            # Sequence (4 bytes, little-endian)
            result.extend(tx_in.sequence.to_bytes(4, 'little'))
        
        # Output count (varint)
        result.extend(self._encode_varint(len(self.tx_outs)))
        
        # Serialize outputs
        for tx_out in self.tx_outs:
            # Amount (8 bytes, little-endian)
            result.extend(tx_out.amount.to_bytes(8, 'little'))
            
            # ScriptPubKey (varint + script)
            script_pubkey = tx_out.script_pubkey.serialize()
            result.extend(self._encode_varint(len(script_pubkey)))
            result.extend(script_pubkey)
        
        # Locktime (4 bytes, little-endian)
        result.extend(self.locktime.to_bytes(4, 'little'))
        
        return bytes(result)

    def is_coinbase(self):
        """Check if this is a coinbase transaction"""
        if len(self.tx_ins) != 1:
            return False
            
        # Check if the previous transaction hash is all zeros (for coinbase)
        first_input = self.tx_ins[0]
        return first_input.prev_tx == '0' * 64  # 64 zeros for a 256-bit hash
        
    def to_dict(self):
        """Convert transaction to dictionary"""
        return {
            'version': self.version,
            'tx_ins': [tx_in.to_dict() for tx_in in self.tx_ins],
            'tx_outs': [tx_out.to_dict() for tx_out in self.tx_outs],
            'locktime': self.locktime,
            'txid': self.id(),
            'is_coinbase': self.is_coinbase()
        }

    @classmethod
    def create_coinbase(cls, amount, script_pubkey, height=0):
        """Create a coinbase transaction (first transaction in a block)
        
        Args:
            amount: The block reward amount in satoshis
            script_pubkey: The Script object containing the recipient's public key hash
            height: The block height (used in the coinbase scriptSig)
            
        Returns:
            A new coinbase transaction
        """
        # Create a special coinbase input
        # The script_sig can contain arbitrary data, but typically includes the block height
        script_sig = Script([height, 'COINBASE'.encode('utf-8')])
        
        tx_in = TxIn(
            prev_tx='0' * 64,  # 32 bytes of zeros for coinbase
            prev_index=0xffffffff,  # Special index for coinbase
            script_sig=script_sig,
            sequence=0xffffffff
        )
        
        # Create the output that sends coins to the miner
        tx_out = TxOut(amount=amount, script_pubkey=script_pubkey)
        
        # Version 1 transaction with locktime 0
        return cls(version=1, tx_ins=[tx_in], tx_outs=[tx_out], locktime=0)

# Example usage
if __name__ == "__main__":
    try:
        # Create a pay-to-pubkey-hash script (simplified)
        pubkey_hash = "1a2b3c4d5e6f7g8h9i0j"  # This would be the actual hash160 of the public key
        script_pubkey = Script(["OP_DUP", "OP_HASH160", pubkey_hash, "OP_EQUALVERIFY", "OP_CHECKSIG"])
        
        # Create a coinbase transaction (miner reward)
        coinbase_tx = Tx.create_coinbase(
            amount=50 * 100_000_000,  # 50 BTC in satoshis
            script_pubkey=script_pubkey,
            height=123456  # Current block height
        )
        
        print("=== Coinbase Transaction ===")
        print(f"Transaction ID: {coinbase_tx.id()}")
        print(f"Is coinbase: {coinbase_tx.is_coinbase()}")
        print(f"Number of inputs: {len(coinbase_tx.tx_ins)}")
        print(f"Number of outputs: {len(coinbase_tx.tx_outs)}")
        print(f"Output amount: {coinbase_tx.tx_outs[0].amount} satoshis")
        
    except Exception as e:
        print(f"Error: {e}")