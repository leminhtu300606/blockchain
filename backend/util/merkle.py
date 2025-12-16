"""
Merkle Tree implementation for calculating Merkle roots and proofs.
This module provides functions to create and verify Merkle trees.
"""

import hashlib
from typing import List, Optional

def double_sha256(data: bytes) -> bytes:
    """Calculate double SHA-256 hash of the input data."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def calculate_merkle_root(tx_hashes: List[str]) -> str:
    """
    Calculate the Merkle root from a list of transaction hashes.
    
    Args:
        tx_hashes: List of transaction hashes as hexadecimal strings
        
    Returns:
        str: The Merkle root as a hexadecimal string (little-endian)
    """
    if not tx_hashes:
        return ""
    
    # Convert all hashes to bytes (little-endian)
    hashes = [bytes.fromhex(h)[::-1] for h in tx_hashes]
    
    while len(hashes) > 1:
        # If odd number of hashes, duplicate the last one
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])
        
        # Create new level of hashes
        new_hashes = []
        for i in range(0, len(hashes), 2):
            # Concatenate and double hash
            concat = hashes[i] + hashes[i+1]
            new_hash = double_sha256(concat)
            new_hashes.append(new_hash)
        
        hashes = new_hashes
    
    # Return as little-endian hex string
    return hashes[0][::-1].hex() if hashes else ""

def verify_merkle_proof(tx_hash: str, merkle_root: str, merkle_path: List[str], index: int) -> bool:
    """
    Verify a Merkle proof for a transaction.
    
    Args:
        tx_hash: The transaction hash to verify
        merkle_root: The expected Merkle root
        merkle_path: List of hashes needed for verification
        index: The position of the transaction in the block
        
    Returns:
        bool: True if the proof is valid, False otherwise
    """
    current = bytes.fromhex(tx_hash)[::-1]  # Convert to little-endian
    
    for i, sibling in enumerate(merkle_path):
        sibling_bytes = bytes.fromhex(sibling)[::-1]
        
        # If the index's bit at position i is 0, current is on the left
        if (index >> i) & 1:
            current = double_sha256(sibling_bytes + current)
        else:
            current = double_sha256(current + sibling_bytes)
    
    return current[::-1].hex() == merkle_root

def get_merkle_path(tx_hashes: List[str], tx_index: int) -> List[str]:
    """
    Get the Merkle path for a transaction at the given index.
    
    Args:
        tx_hashes: List of all transaction hashes
        tx_index: Index of the transaction to get the path for
        
    Returns:
        List[str]: List of hashes needed to verify the transaction
    """
    if not tx_hashes or tx_index >= len(tx_hashes):
        return []
    
    # Convert all hashes to bytes (little-endian)
    level = [bytes.fromhex(h)[::-1] for h in tx_hashes]
    path = []
    index = tx_index
    
    while len(level) > 1:
        if len(level) % 2 != 0:
            level.append(level[-1])
        
        new_level = []
        for i in range(0, len(level), 2):
            if i == index or i == index - 1:
                # If this pair contains our transaction, add the other hash to the path
                if i == index:
                    path.append(level[i+1][::-1].hex())  # Convert back to big-endian
                else:
                    path.append(level[i][::-1].hex())  # Convert back to big-endian
                    index = i // 2
                    new_level.append(double_sha256(level[i] + level[i+1]))
                    continue
            
            new_hash = double_sha256(level[i] + level[i+1])
            new_level.append(new_hash)
        
        level = new_level
        index = index // 2
    
    return path

# Example usage
if __name__ == "__main__":
    # Example transaction hashes (in reality these would be actual transaction hashes)
    tx_hashes = [
        "tx1_hash_1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
        "tx2_hash_1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
        "tx3_hash_1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
        "tx4_hash_1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd"
    ]
    
    # Calculate Merkle root
    merkle_root = calculate_merkle_root(tx_hashes)
    print(f"Merkle Root: {merkle_root}")
    
    # Get Merkle proof for first transaction
    tx_index = 0
    merkle_path = get_merkle_path(tx_hashes, tx_index)
    print(f"\nMerkle Path for tx at index {tx_index}:")
    for i, h in enumerate(merkle_path):
        print(f"  Level {i}: {h}")
    
    # Verify the Merkle proof
    is_valid = verify_merkle_proof(
        tx_hash=tx_hashes[tx_index],
        merkle_root=merkle_root,
        merkle_path=merkle_path,
        index=tx_index
    )
    print(f"\nMerkle Proof is {'valid' if is_valid else 'invalid'}")