"""
Account Module - Bitcoin Account/Wallet Management

Module này cung cấp class Account để:
- Tạo keypair mới (private key, public key)
- Generate Bitcoin address từ public key
- Quản lý keys

Workflow tạo Bitcoin Address:
1. Generate private key (32 bytes random)
2. Private key → Public key (ECDSA secp256k1)
3. Public key → SHA256 → RIPEMD160 = pubkey_hash
4. Add version byte (0x00 for mainnet)
5. Add checksum (double SHA256)
6. Base58 encode → Bitcoin Address

Example:
    account = Account()
    keys = account.create_keys()
    print(f"Address: {keys['address']}")
"""
import hashlib
import os
import logging
from typing import Optional, Dict

import ecdsa
import base58


# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Bitcoin mainnet version byte
MAINNET_VERSION = b'\x00'

# Testnet version byte
TESTNET_VERSION = b'\x6f'


# =============================================================================
# ACCOUNT CLASS
# =============================================================================

class Account:
    """
    Bitcoin Account - Quản lý private key, public key, và address.
    
    Có thể:
    - Tạo account mới với keypair random
    - Import account từ private key có sẵn
    
    Security Note:
    - Private key phải được bảo mật tuyệt đối
    - Không bao giờ log hoặc expose private key
    
    Attributes:
        private_key: 32 bytes private key
        public_key: Compressed public key (33 bytes)
        address: Bitcoin address (Base58Check encoded)
        
    Example:
        # Tạo account mới
        account = Account()
        keys = account.create_keys()
        
        # Import từ private key
        account = Account(private_key="hex_of_private_key")
        keys = account.create_keys()
    """
    
    __slots__ = ['private_key', 'public_key', 'address', '_version']
    
    def __init__(self, private_key: Optional[str] = None, testnet: bool = False):
        """
        Khởi tạo Account.
        
        Args:
            private_key: Private key hex string (optional)
                         Nếu không cung cấp, sẽ generate key mới
            testnet: Sử dụng testnet address format (default: False)
        """
        self.private_key: Optional[bytes] = None
        self.public_key: Optional[bytes] = None
        self.address: Optional[str] = None
        self._version = TESTNET_VERSION if testnet else MAINNET_VERSION
        
        # Import private key nếu có
        if private_key:
            if isinstance(private_key, str):
                self.private_key = bytes.fromhex(private_key)
            else:
                self.private_key = private_key
    
    # =========================================================================
    # KEY GENERATION
    # =========================================================================
    
    def create_keys(self) -> Dict[str, str]:
        """
        Tạo keypair và Bitcoin address.
        
        Nếu private key chưa có, sẽ generate mới.
        
        Returns:
            dict: {
                'private_key': hex string,
                'public_key': hex string,
                'address': Base58Check encoded address
            }
        """
        # Generate private key nếu chưa có
        if not self.private_key:
            self.private_key = self._generate_private_key()
        
        # Derive public key
        self.public_key = self._derive_public_key()
        
        # Generate address
        self.address = self._generate_address()
        
        logger.info(f"Account created: {self.address}")
        
        return {
            'private_key': self.private_key.hex(),
            'public_key': self.public_key.hex(),
            'address': self.address
        }
    
    def _generate_private_key(self) -> bytes:
        """
        Generate private key ngẫu nhiên.
        
        Sử dụng os.urandom() để đảm bảo cryptographically secure.
        
        Returns:
            bytes: 32-byte private key
        """
        return os.urandom(32)
    
    def _derive_public_key(self) -> bytes:
        """
        Derive public key từ private key.
        
        Sử dụng ECDSA với curve secp256k1 (chuẩn Bitcoin).
        Trả về compressed public key (33 bytes).
        
        Compressed format:
        - Prefix 0x02 nếu y là số chẵn
        - Prefix 0x03 nếu y là số lẻ
        - Theo sau là x coordinate (32 bytes)
        
        Returns:
            bytes: Compressed public key (33 bytes)
        """
        # Tạo signing key từ private key
        signing_key = ecdsa.SigningKey.from_string(
            self.private_key, 
            curve=ecdsa.SECP256k1
        )
        
        # Get verifying key (public key)
        verifying_key = signing_key.get_verifying_key()
        
        # Get raw public key point (x, y)
        # verifying_key.to_string() returns x || y (64 bytes)
        raw_pubkey = verifying_key.to_string()
        x = raw_pubkey[:32]
        y = raw_pubkey[32:]
        
        # Compress: prefix + x
        # Prefix: 0x02 if y is even, 0x03 if y is odd
        prefix = b'\x02' if y[-1] % 2 == 0 else b'\x03'
        
        return prefix + x
    
    # =========================================================================
    # ADDRESS GENERATION
    # =========================================================================
    
    def _generate_address(self) -> str:
        """
        Generate Bitcoin address từ public key.
        
        Process (P2PKH):
        1. SHA256(public_key)
        2. RIPEMD160(sha256_hash) = pubkey_hash (20 bytes)
        3. version_byte + pubkey_hash
        4. checksum = SHA256(SHA256(3))[:4]
        5. Base58Check(version + hash + checksum)
        
        Returns:
            str: Bitcoin address
        """
        # Step 1: SHA256
        sha256_hash = hashlib.sha256(self.public_key).digest()
        
        # Step 2: RIPEMD160
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
        
        # Step 3: Add version byte
        versioned = self._version + ripemd160_hash
        
        # Step 4: Calculate checksum (first 4 bytes of double SHA256)
        checksum = hashlib.sha256(
            hashlib.sha256(versioned).digest()
        ).digest()[:4]
        
        # Step 5: Base58 encode
        binary_address = versioned + checksum
        address = base58.b58encode(binary_address).decode('utf-8')
        
        return address
    
    # =========================================================================
    # GETTERS
    # =========================================================================
    
    def get_private_key(self) -> Optional[str]:
        """
        Lấy private key dạng hex.
        
        ⚠️ Security Warning: Chỉ sử dụng khi thực sự cần thiết!
        """
        return self.private_key.hex() if self.private_key else None
    
    def get_public_key(self) -> Optional[str]:
        """Lấy public key dạng hex."""
        return self.public_key.hex() if self.public_key else None
    
    def get_address(self) -> Optional[str]:
        """Lấy Bitcoin address."""
        return self.address
    
    def get_pubkey_hash(self) -> Optional[str]:
        """
        Lấy public key hash (dùng trong scripts).
        
        pubkey_hash = RIPEMD160(SHA256(public_key))
        """
        if not self.public_key:
            return None
        
        sha256_hash = hashlib.sha256(self.public_key).digest()
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
        return ripemd160_hash.hex()
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    # =========================================================================
    # STORAGE & ENCRYPTION
    # =========================================================================
    
    def save_to_file(self, filepath: str, password: str = None) -> bool:
        """
        Lưu account vào file (có mã hóa nếu cung cấp password).
        """
        import json
        
        data = {
            'address': self.address,
            'public_key': self.public_key.hex() if self.public_key else None
        }
        
        if self.private_key:
            if password:
                # Encrypt private key using simple XOR with PBKDF2 derived key
                salt = os.urandom(16)
                key = hashlib.pbkdf2_hmac(
                    'sha256', 
                    password.encode('utf-8'), 
                    salt, 
                    100000,
                    dklen=32
                )
                
                # XOR
                encrypted_key = bytes(a ^ b for a, b in zip(self.private_key, key))
                
                data['encryption'] = {
                    'method': 'pbkdf2_xor',
                    'salt': salt.hex(),
                    'encrypted_privkey': encrypted_key.hex()
                }
            else:
                # Plain text (Warning: Unsafe)
                data['private_key'] = self.private_key.hex()
                
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving account: {e}")
            return False

    @classmethod
    def load_from_file(cls, filepath: str, password: str = None) -> 'Account':
        """
        Load account từ file (cần password nếu đã mã hóa).
        """
        import json
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        account = cls()
        account.address = data.get('address')
        if data.get('public_key'):
            account.public_key = bytes.fromhex(data['public_key'])
            
        # Recover private key
        if 'encryption' in data:
            if not password:
                raise ValueError("Password required to decrypt wallet")
                
            enc_data = data['encryption']
            if enc_data['method'] != 'pbkdf2_xor':
                raise ValueError("Unsupported encryption method")
                
            salt = bytes.fromhex(enc_data['salt'])
            encrypted_key = bytes.fromhex(enc_data['encrypted_privkey'])
            
            # Derive key again
            key = hashlib.pbkdf2_hmac(
                'sha256', 
                password.encode('utf-8'), 
                salt, 
                100000,
                dklen=32
            )
            
            # XOR to decrypt
            account.private_key = bytes(a ^ b for a, b in zip(encrypted_key, key))
            
        elif 'private_key' in data:
            if password:
                 logger.warning("Password provided but wallet is not encrypted")
            account.private_key = bytes.fromhex(data['private_key'])
            
        return account

    def __repr__(self) -> str:
        return f"Account(address={self.address})"


# =============================================================================
# STANDALONE FUNCTIONS
# =============================================================================

def generate_account(testnet: bool = False) -> Dict[str, str]:
    """
    Helper function để tạo account mới nhanh chóng.
    
    Args:
        testnet: Sử dụng testnet format
        
    Returns:
        dict: {'private_key', 'public_key', 'address'}
    """
    account = Account(testnet=testnet)
    return account.create_keys()


def import_account(private_key: str, testnet: bool = False) -> Dict[str, str]:
    """
    Import account từ private key.
    
    Args:
        private_key: Private key hex string
        testnet: Sử dụng testnet format
        
    Returns:
        dict: {'private_key', 'public_key', 'address'}
    """
    account = Account(private_key=private_key, testnet=testnet)
    return account.create_keys()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("BITCOIN ACCOUNT DEMO")
    print("=" * 60)
    
    # Tạo account mới
    print("\n📱 Creating new account...")
    account = Account()
    keys = account.create_keys()
    
    print(f"\n🔐 Private Key: {keys['private_key'][:16]}...{keys['private_key'][-16:]}")
    print(f"🔑 Public Key: {keys['public_key'][:20]}...")
    print(f"📬 Address: {keys['address']}")
    print(f"🔗 PubKey Hash: {account.get_pubkey_hash()}")
    
    # Tạo testnet account
    print("\n📱 Creating testnet account...")
    testnet_account = Account(testnet=True)
    testnet_keys = testnet_account.create_keys()
    print(f"📬 Testnet Address: {testnet_keys['address']}")
