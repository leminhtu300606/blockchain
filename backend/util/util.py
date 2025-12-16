"""
Utility Module - Cryptographic Hash Functions

Module chứa các hàm tiện ích crypto được sử dụng xuyên suốt codebase.
"""
import hashlib


def hash256(data: bytes) -> bytes:
    """
    Double SHA-256 hash (chuẩn Bitcoin).
    
    hash256(data) = SHA256(SHA256(data))
    
    Được sử dụng cho:
    - Block header hashing
    - Transaction ID calculation
    - Signature hashing
    
    Args:
        data: Dữ liệu cần hash (bytes)
        
    Returns:
        bytes: 32-byte hash result
        
    Example:
        >>> hash256(b"hello").hex()[:16]
        '9595c9df90075148...'
    """
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def hash160(data: bytes) -> bytes:
    """
    HASH160 = RIPEMD160(SHA256(data)).
    
    Được sử dụng để tạo public key hash cho P2PKH addresses.
    
    Args:
        data: Dữ liệu cần hash (thường là public key)
        
    Returns:
        bytes: 20-byte hash result
    """
    sha256_hash = hashlib.sha256(data).digest()
    return hashlib.new('ripemd160', sha256_hash).digest()


def sha256(data: bytes) -> bytes:
    """
    Single SHA-256 hash.
    
    Args:
        data: Dữ liệu cần hash
        
    Returns:
        bytes: 32-byte hash result
    """
    return hashlib.sha256(data).digest()