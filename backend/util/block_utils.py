"""
Block Utilities Module - Tạo và quản lý Blocks

Module này cung cấp các utility functions và classes để:
- Tạo block mới với transactions
- Tạo genesis block
- Thêm transactions vào block

Classes:
- BlockBuilder: Builder pattern để tạo block step-by-step
- BlockCreationError: Exception cho lỗi tạo block

Functions:
- create_genesis_block(): Tạo block đầu tiên
- add_transactions_to_block(): Thêm txs vào block đã tồn tại
"""
import json
import time
import logging
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING

# Local imports to avoid circular dependency
from core.block import Block
from core.Tx import Tx, TxIn, TxOut, Script
from core.mempool import mempool
from core.transaction_verifier import verify_transaction
from .merkle import calculate_merkle_root

if TYPE_CHECKING:
    from core.blockheader import BlockHeader

# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

ZERO_HASH = '0' * 64  # 32 bytes zeros
DEFAULT_DIFFICULTY = '1d00ffff'
DEFAULT_BLOCK_SIZE_LIMIT = 1_000_000  # 1 MB


# =============================================================================
# EXCEPTIONS
# =============================================================================

class BlockCreationError(Exception):
    """Exception được raise khi có lỗi trong quá trình tạo block."""
    pass


# =============================================================================
# BLOCK BUILDER CLASS
# =============================================================================

class BlockBuilder:
    """
    Block Builder - Tạo block theo pattern Builder.
    """
    
    def __init__(
        self, 
        previous_block_hash: str, 
        difficulty_bits: str = DEFAULT_DIFFICULTY
    ):
        """Khởi tạo BlockBuilder."""
        self.transactions: List[Tx] = []
        self.previous_block_hash = previous_block_hash
        self.difficulty_bits = difficulty_bits
        self.coinbase_tx: Optional[Dict[str, Any]] = None
        self.version = 1
        
        logger.debug(f"BlockBuilder initialized with prev_hash: {previous_block_hash[:16]}...")
    
    def set_coinbase_transaction(
        self, 
        miner_address: str, 
        reward: int, 
        height: int
    ) -> None:
        """Tạo và set coinbase transaction."""
        self.coinbase_tx = {
            'txid': ZERO_HASH,
            'vin': [{
                'coinbase': f'03{height:08x}',
                'sequence': 0xffffffff
            }],
            'vout': [{
                'value': reward,
                'scriptPubKey': {
                    'address': miner_address,
                    'asm': f'OP_DUP OP_HASH160 {miner_address} OP_EQUALVERIFY OP_CHECKSIG',
                    'hex': '76a914' + '00' * 20 + '88ac',
                    'type': 'pubkeyhash'
                }
            }],
            'version': 1,
            'locktime': 0
        }
        logger.info(f"Coinbase set: reward={reward} satoshis, height={height}")
    
    def add_transaction(
        self, 
        tx: Tx, 
        utxo_set: Dict[str, Dict[int, Dict[str, Any]]]
    ) -> bool:
        """Thêm transaction vào block (nếu hợp lệ)."""
        txid = tx.id()
        if not verify_transaction(tx, utxo_set):
            return False
        for existing_tx in self.transactions:
            if existing_tx.id() == txid:
                return False
        self.transactions.append(tx)
        return True
    
    def create_block(self, height: int) -> Block:
        """Tạo block hoàn chỉnh."""
        # Import local để tránh circular dependency
        from core.blockheader import BlockHeader
        
        if not self.coinbase_tx:
            raise BlockCreationError("Coinbase transaction not set")
        
        tx_hashes = [self.coinbase_tx['txid']]
        tx_hashes.extend(tx.id() for tx in self.transactions)
        
        merkle_root = calculate_merkle_root(tx_hashes)
        
        header = BlockHeader(
            version=self.version,
            previous_block_hash=self.previous_block_hash,
            merkle_root=merkle_root,
            bits=self.difficulty_bits
        )
        
        all_txs = [self.coinbase_tx] + [tx.to_dict() for tx in self.transactions]
        block_size = len(json.dumps(all_txs, default=str).encode('utf-8'))
        
        return Block(
            Height=height,
            Blocksize=block_size,
            Blockheader=header,
            Txcount=len(all_txs),
            Txs=all_txs
        )


# =============================================================================
# GENESIS BLOCK CREATION
# =============================================================================

def create_genesis_block(
    coinbase_tx: Dict[str, Any], 
    timestamp: Optional[int] = None
) -> Block:
    """Tạo Genesis Block."""
    # Import local để tránh circular dependency
    from core.blockheader import BlockHeader
    
    header = BlockHeader(
        version=1,
        previous_block_hash=ZERO_HASH,
        merkle_root=coinbase_tx.get('txid', ZERO_HASH),
        timestamp=timestamp or int(time.time()),
        bits=DEFAULT_DIFFICULTY
    )
    
    block_size = len(json.dumps([coinbase_tx], default=str))
    
    return Block(
        Height=0,
        Blocksize=block_size,
        Blockheader=header,
        Txcount=1,
        Txs=[coinbase_tx]
    )


# =============================================================================
# TRANSACTION ADDITION
# =============================================================================

def add_transactions_to_block(
    block: Block, 
    transactions: List[Tx], 
    utxo_set: Dict[str, Dict[int, Dict[str, Any]]]
) -> Tuple[Block, List[Tx]]:
    """Thêm transactions vào block đã tồn tại."""
    added_txs: List[Tx] = []
    
    for tx in transactions:
        try:
            if block.Blocksize > DEFAULT_BLOCK_SIZE_LIMIT:
                logger.warning("Block size limit reached")
                break
            
            if not verify_transaction(tx, utxo_set):
                continue
            
            block.Txs.append(tx.to_dict())
            block.Txcount += 1
            block.Blocksize += len(json.dumps(tx.to_dict(), default=str))
            added_txs.append(tx)
            
            _update_utxo_set(tx, utxo_set)
            
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            continue
    
    if added_txs:
        tx_hashes = []
        for tx_data in block.Txs:
            if isinstance(tx_data, dict):
                tx_hashes.append(tx_data.get('txid', ZERO_HASH))
            else:
                tx_hashes.append(tx_data.id())
        
        block.Blockheader.merkle_root = calculate_merkle_root(tx_hashes)
    
    logger.info(f"Added {len(added_txs)} transactions to block")
    return block, added_txs


def _update_utxo_set(
    tx: Tx, 
    utxo_set: Dict[str, Dict[int, Dict[str, Any]]]
) -> None:
    """Cập nhật UTXO set."""
    txid = tx.id()
    
    for tx_in in tx.tx_ins:
        if tx_in.prev_tx in utxo_set:
            utxo_set[tx_in.prev_tx].pop(tx_in.prev_index, None)
    
    utxo_set[txid] = {}
    for i, tx_out in enumerate(tx.tx_outs):
        utxo_set[txid][i] = {
            'amount': tx_out.amount,
            'script_pubkey': tx_out.script_pubkey
        }
