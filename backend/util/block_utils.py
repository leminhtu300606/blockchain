"""
Block utilities for creating and managing blocks with transactions.
This module provides functionality to add transactions to blocks and manage the block creation process.
"""
import hashlib
import json
import time
import sys
import os
from typing import List, Dict, Any, Optional, Tuple

# Add the parent directory to the path to allow relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.block import Block
from core.blockheader import BlockHeader
from core.Tx import Tx, Script
from core.mempool import mempool
from .tx_utils import verify_transaction

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlockCreationError(Exception):
    """Exception raised for errors during block creation."""
    pass

def calculate_merkle_root(tx_hashes: List[str]) -> str:
    """
    Calculate the Merkle root from a list of transaction hashes.
    
    Args:
        tx_hashes: List of transaction hashes
        
    Returns:
        str: The Merkle root as a hexadecimal string
    """
    if not tx_hashes:
        return ""
    
    # Convert all hashes to bytes
    hashes = [bytes.fromhex(tx_hash) for tx_hash in tx_hashes]
    
    while len(hashes) > 1:
        # If the number of hashes is odd, duplicate the last one
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])
        
        # Create a new level of the Merkle tree
        new_hashes = []
        for i in range(0, len(hashes), 2):
            # Concatenate the two hashes and hash them
            concat = hashes[i] + hashes[i+1]
            new_hash = hashlib.sha256(hashlib.sha256(concat).digest()).digest()
            new_hashes.append(new_hash)
        
        hashes = new_hashes
    
    return hashes[0].hex() if hashes else ""

class BlockBuilder:
    """
    A class to help build and manage blocks with transactions.
    """
    
    def __init__(self, previous_block_hash: str, difficulty_bits: str = '1d00ffff'):
        """
        Initialize the BlockBuilder.
        
        Args:
            previous_block_hash: Hash of the previous block
            difficulty_bits: Difficulty target in compact format
        """
        self.transactions: List[Tx] = []
        self.previous_block_hash = previous_block_hash
        self.difficulty_bits = difficulty_bits
        self.coinbase_tx = None
        self.version = 1
        
    def set_coinbase_transaction(self, miner_address: str, reward: int, height: int) -> None:
        """
        Create and set the coinbase transaction for the block.
        
        Args:
            miner_address: The address to receive the block reward
            reward: The block reward amount in satoshis
            height: The height of the block
        """
        # In a real implementation, you would create a proper coinbase transaction
        # For now, we'll create a simplified version
        self.coinbase_tx = {
            'txid': '0' * 64,  # Placeholder for coinbase txid
            'vin': [{
                'coinbase': f'03{height:08x}',  # Height in hex
                'sequence': 0xffffffff
            }],
            'vout': [{
                'value': reward,
                'scriptPubKey': {
                    'address': miner_address,
                    'asm': f'OP_DUP OP_HASH160 {miner_address} OP_EQUALVERIFY OP_CHECKSIG',
                    'hex': '76a914' + '00' * 20 + '88ac',  # Simplified script
                    'type': 'pubkeyhash'
                }
            }],
            'version': 1,
            'locktime': 0
        }
    
    def add_transaction(self, tx: Tx, utxo_set: Dict[str, Dict[int, Dict[str, Any]]]) -> bool:
        """
        Add a transaction to the block if it's valid.
        
        Args:
            tx: The transaction to add
            utxo_set: The current UTXO set
            
        Returns:
            bool: True if the transaction was added, False otherwise
        """
        # Verify the transaction
        if not verify_transaction(tx, utxo_set):
            logger.warning(f"Invalid transaction {tx.id()}, not adding to block")
            return False
        
        # Check for duplicate transactions
        if any(t.id() == tx.id() for t in self.transactions):
            logger.warning(f"Duplicate transaction {tx.id()}, not adding to block")
            return False
        
        # Add the transaction
        self.transactions.append(tx)
        logger.info(f"Added transaction {tx.id()} to block")
        return True
    
    def create_block(self, height: int) -> Block:
        """
        Create a new block with the current transactions.
        
        Args:
            height: The height of the new block
            
        Returns:
            Block: The newly created block
        """
        if not self.coinbase_tx:
            raise BlockCreationError("Coinbase transaction not set")
        
        # Get transaction hashes (starting with coinbase)
        tx_hashes = [self.coinbase_tx['txid']]  # Coinbase txid is all zeros
        tx_hashes.extend(tx.id() for tx in self.transactions)
        
        # Calculate Merkle root
        merkle_root = calculate_merkle_root(tx_hashes)
        
        # Create block header
        header = BlockHeader(
            version=self.version,
            previous_block_hash=self.previous_block_hash,
            merkle_root=merkle_root,
            bits=self.difficulty_bits
        )
        
        # Create block with transactions (coinbase first)
        all_transactions = [self.coinbase_tx] + [tx.to_dict() for tx in self.transactions]
        
        # Calculate block size (simplified)
        block_size = len(json.dumps(all_transactions, default=str).encode('utf-8'))
        
        # Create and return the block
        return Block(
            Height=height,
            Blocksize=block_size,
            Blockheader=header,
            Txcount=len(all_transactions),
            Txs=all_transactions
        )

def create_genesis_block(coinbase_tx: Dict, timestamp: int = None) -> Block:
    """
    Create the genesis (first) block.
    
    Args:
        coinbase_tx: The coinbase transaction for the genesis block
        timestamp: Optional timestamp (defaults to current time)
        
    Returns:
        Block: The genesis block
    """
    # Create a block with no previous hash
    header = BlockHeader(
        version=1,
        previous_block_hash='0' * 64,  # All zeros for genesis block
        merkle_root=coinbase_tx['txid'],  # Only the coinbase transaction
        timestamp=timestamp or int(time.time()),
        bits='1d00ffff'  # Default difficulty
    )
    
    # Create the genesis block
    return Block(
        Height=0,
        Blocksize=len(json.dumps([coinbase_tx])),
        Blockheader=header,
        Txcount=1,  # Only the coinbase transaction
        Txs=[coinbase_tx]
    )

def add_transactions_to_block(block: Block, transactions: List[Tx], utxo_set: Dict) -> Tuple[Block, List[Tx]]:
    """
    Add valid transactions to a block and return the updated block and list of added transactions.
    
    Args:
        block: The block to add transactions to
        transactions: List of transactions to add
        utxo_set: Current UTXO set for validation
        
    Returns:
        Tuple[Block, List[Tx]]: Updated block and list of added transactions
    """
    added_txs = []
    
    for tx in transactions:
        try:
            # Skip if block is getting too big (simplified check)
            if block.Blocksize > 1000000:  # 1MB block size limit (adjust as needed)
                logger.warning("Block size limit reached, stopping transaction addition")
                break
                
            # Verify and add the transaction
            if verify_transaction(tx, utxo_set):
                # Add to block (simplified - in a real implementation, you'd update the merkle tree)
                block.Txs.append(tx.to_dict())
                block.Txcount += 1
                block.Blocksize += len(str(tx.to_dict()))  # Simplified size calculation
                added_txs.append(tx)
                
                # Update UTXO set (in a real implementation, you'd do this after block confirmation)
                # This is a simplified version
                for tx_in in tx.tx_ins:
                    if tx_in.prev_tx in utxo_set and tx_in.prev_index in utxo_set[tx_in.prev_tx]:
                        del utxo_set[tx_in.prev_tx][tx_in.prev_index]
                
                # Add new outputs to UTXO set
                tx_id = tx.id()
                utxo_set[tx_id] = {}
                for i, tx_out in enumerate(tx.tx_outs):
                    utxo_set[tx_id][i] = {
                        'amount': tx_out.amount,
                        'script_pubkey': tx_out.script_pubkey
                    }
                
                logger.info(f"Added transaction {tx_id} to block")
            
        except Exception as e:
            logger.error(f"Error adding transaction to block: {e}")
            continue
    
    # Update the Merkle root if any transactions were added
    if added_txs:
        tx_hashes = [tx['txid'] if isinstance(tx, dict) else tx.id() for tx in block.Txs]
        block.Blockheader.merkle_root = calculate_merkle_root(tx_hashes)
    
    return block, added_txs
