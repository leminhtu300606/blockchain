from util.util import hash256
import time

class BlockHeader:
    """Represents a block header in the blockchain."""
    
    def __init__(self, version, previous_block_hash, merkle_root, timestamp=None, bits=None):
        """
        Initialize a new block header.
        
        Args:
            version (int): Block version number
            previous_block_hash (str): Hash of the previous block
            merkle_root (str): Merkle root of transactions in the block
            timestamp (int, optional): Block creation timestamp. Defaults to current time.
            bits (str, optional): Difficulty target in compact format. Defaults to '1d00ffff'.
        """
        self.version = version
        self.previous_block_hash = previous_block_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp or int(time.time())
        self.bits = bits or '1d00ffff'  # Default difficulty target
        self.nonce = 0
        self.block_hash = None
    
    def mine(self):
        """Mine the block by finding a valid nonce that satisfies the difficulty target."""
        print("Mining block...")
        self.nonce = 0
        target = self.calculate_target()
        
        while True:
            # Serialize block header with current nonce
            header_hex = self.serialize()
            
            # Calculate double SHA-256 hash
            hash_result = hash256(bytes.fromhex(header_hex)).hex()
            
            # Check if hash meets the target difficulty
            if int(hash_result, 16) < target:
                self.block_hash = hash_result
                print(f"\nBlock mined! Hash: {self.block_hash}")
                print(f"Nonce: {self.nonce}")
                return self.block_hash
            
            self.nonce += 1
            if self.nonce % 100000 == 0:  # Print progress every 100k hashes
                print(f"Hashing... Nonce: {self.nonce}, Hash: {hash_result[:16]}...", end="\r")
    
    def calculate_target(self):
        """Calculate the target from bits."""
        # This is a simplified version - in a real implementation, you'd need to handle
        # the actual Bitcoin difficulty calculation
        return 0x0000ffff00000000000000000000000000000000000000000000000000000000
    
    def serialize(self):
        """Serialize the block header to a hexadecimal string."""
        # Version (4 bytes, little-endian)
        version = self.version.to_bytes(4, 'little').hex()
        
        # Previous block hash (32 bytes, little-endian)
        prev_hash = bytes.fromhex(self.previous_block_hash)[::-1].hex()
        
        # Merkle root (32 bytes, little-endian)
        merkle = bytes.fromhex(self.merkle_root)[::-1].hex()
        
        # Timestamp (4 bytes, little-endian)
        timestamp = self.timestamp.to_bytes(4, 'little').hex()
        
        # Bits (4 bytes, little-endian)
        bits = bytes.fromhex(self.bits)[::-1].hex()
        
        # Nonce (4 bytes, little-endian)
        nonce = self.nonce.to_bytes(4, 'little').hex()
        
        # Concatenate all fields
        return version + prev_hash + merkle + timestamp + bits + nonce
    
    def to_dict(self):
        """Convert block header to dictionary for serialization."""
        return {
            'version': self.version,
            'previous_block_hash': self.previous_block_hash,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'bits': self.bits,
            'nonce': self.nonce,
            'block_hash': self.block_hash
        }
