import hashlib
import ecdsa
import base58
import os


class Account:
    def __init__(self, private_key=None):
        """
        Initialize an account with an existing private key or generate a new one.
        If private_key is None, a new key pair will be generated.
        """
        self.private_key = None
        self.public_key = None
        self.address = None
        
        if private_key:
            if isinstance(private_key, str):
                self.private_key = bytes.fromhex(private_key)
            else:
                self.private_key = private_key
    
    def create_keys(self):
        """Generate a new key pair and Bitcoin address."""
        # Generate a new private key if one doesn't exist
        if not self.private_key:
            self.private_key = os.urandom(32)
        
        # Generate public key from private key
        self.public_key = self._generate_public_key()
        
        # Generate Bitcoin address from public key
        self.address = self._generate_address()
        
        return {
            'private_key': self.private_key.hex(),
            'public_key': self.public_key.hex(),
            'address': self.address
        }
    
    def _generate_public_key(self):
        """Generate a public key from the private key using SECP256k1."""
        signing_key = ecdsa.SigningKey.from_string(self.private_key, curve=ecdsa.SECP256k1)
        verifying_key = signing_key.get_verifying_key()
        return b'\x02' + verifying_key.to_string()[:32]  # Compressed format
    
    def _generate_address(self):
        """Generate a Bitcoin address from the public key."""
        # Step 1: Perform SHA-256 hashing on the public key
        sha256_hash = hashlib.sha256(self.public_key).digest()
        
        # Step 2: Perform RIPEMD-160 hashing on the result of SHA-256
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
        
        # Step 3: Add version byte (0x00 for mainnet)
        version_ripemd160 = b'\x00' + ripemd160_hash
        
        # Step 4: Perform double SHA-256 for checksum
        checksum = hashlib.sha256(hashlib.sha256(version_ripemd160).digest()).digest()[:4]
        
        # Step 5: Add checksum to the extended RIPEMD-160 hash
        binary_address = version_ripemd160 + checksum
        
        # Step 6: Convert to Base58Check encoding
        return base58.b58encode(binary_address).decode('utf-8')
    
    def get_private_key(self):
        """Return the private key in hexadecimal format."""
        return self.private_key.hex() if self.private_key else None
    
    def get_public_key(self):
        """Return the public key in hexadecimal format."""
        return self.public_key.hex() if self.public_key else None
    
    def get_address(self):
        """Return the Bitcoin address."""
        return self.address


# Example usage
if __name__ == "__main__":
    # Create a new account and generate keys
    account = Account()
    keys = account.create_keys()
    
    print(f"Private Key: {keys['private_key']}")
    print(f"Public Key: {keys['public_key']}")
    print(f"Bitcoin Address: {keys['address']}")
