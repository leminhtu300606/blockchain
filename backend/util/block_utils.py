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
from typing import List, Dict, Any, Optional, Tuple

from core.block import Block
from core.blockheader import BlockHeader
from core.Tx import Tx, Script
from core.mempool import mempool
from .tx_utils import verify_transaction
from .merkle import calculate_merkle_root  # Import từ merkle.py, không duplicate


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
    
    Workflow sử dụng:
    1. Khởi tạo với previous block hash
    2. Set coinbase transaction (block reward)
    3. Thêm các transactions từ mempool
    4. Gọi create_block() để hoàn thành
    
    Example:
        builder = BlockBuilder(previous_block_hash)
        builder.set_coinbase_transaction(miner_address, reward, height)
        builder.add_transaction(tx, utxo_set)
        block = builder.create_block(height)
    
    Attributes:
        transactions: Danh sách transactions đã thêm
        previous_block_hash: Hash của block trước
        difficulty_bits: Difficulty target
        coinbase_tx: Coinbase transaction
        version: Block version
    """
    
    def __init__(
        self, 
        previous_block_hash: str, 
        difficulty_bits: str = DEFAULT_DIFFICULTY
    ):
        """
        Khởi tạo BlockBuilder.
        
        Args:
            previous_block_hash: Hash của block trước (64 hex chars)
            difficulty_bits: Difficulty target dạng compact
        """
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
        """
        Tạo và set coinbase transaction.
        
        Coinbase là transaction đặc biệt ở đầu mỗi block:
        - Không có input thực
        - Output chứa block reward + transaction fees
        
        Args:
            miner_address: Địa chỉ nhận block reward
            reward: Số satoshis (block reward + fees)
            height: Block height (dùng trong scriptSig)
        """
        self.coinbase_tx = {
            'txid': ZERO_HASH,  # Coinbase txid sẽ được tính sau
            'vin': [{
                'coinbase': f'03{height:08x}',  # Height theo BIP34
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
        """
        Thêm transaction vào block (nếu hợp lệ).
        
        Validation:
        1. Verify transaction (signature, inputs, outputs)
        2. Kiểm tra duplicate
        
        Args:
            tx: Transaction cần thêm
            utxo_set: UTXO set hiện tại để verify
            
        Returns:
            bool: True nếu thêm thành công
        """
        txid = tx.id()
        
        # Verify transaction
        if not verify_transaction(tx, utxo_set):
            logger.warning(f"Invalid transaction: {txid[:16]}...")
            return False
        
        # Check duplicate
        for existing_tx in self.transactions:
            if existing_tx.id() == txid:
                logger.warning(f"Duplicate transaction: {txid[:16]}...")
                return False
        
        # Add transaction
        self.transactions.append(tx)
        logger.debug(f"Added transaction: {txid[:16]}...")
        return True
    
    def create_block(self, height: int) -> Block:
        """
        Tạo block hoàn chỉnh với tất cả transactions.
        
        Steps:
        1. Verify coinbase đã được set
        2. Thu thập tất cả tx hashes
        3. Tính Merkle root
        4. Tạo block header
        5. Tạo Block object
        
        Args:
            height: Block height
            
        Returns:
            Block: Block object hoàn chỉnh
            
        Raises:
            BlockCreationError: Nếu coinbase chưa được set
        """
        if not self.coinbase_tx:
            raise BlockCreationError("Coinbase transaction not set")
        
        # Thu thập tx hashes (coinbase first)
        tx_hashes = [self.coinbase_tx['txid']]
        tx_hashes.extend(tx.id() for tx in self.transactions)
        
        # Tính Merkle root
        merkle_root = calculate_merkle_root(tx_hashes)
        
        # Tạo block header
        header = BlockHeader(
            version=self.version,
            previous_block_hash=self.previous_block_hash,
            merkle_root=merkle_root,
            bits=self.difficulty_bits
        )
        
        # Prepare all transactions
        all_txs = [self.coinbase_tx] + [tx.to_dict() for tx in self.transactions]
        
        # Tính block size
        block_size = len(json.dumps(all_txs, default=str).encode('utf-8'))
        
        logger.info(f"Created block: height={height}, txs={len(all_txs)}, size={block_size}")
        
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
    """
    Tạo Genesis Block (block đầu tiên).
    
    Genesis block có đặc điểm:
    - Height = 0
    - Previous block hash = zeros
    - Chỉ chứa coinbase transaction
    
    Args:
        coinbase_tx: Coinbase transaction dict
        timestamp: Unix timestamp, mặc định là now
        
    Returns:
        Block: Genesis block
    """
    # Genesis block header
    header = BlockHeader(
        version=1,
        previous_block_hash=ZERO_HASH,
        merkle_root=coinbase_tx.get('txid', ZERO_HASH),
        timestamp=timestamp or int(time.time()),
        bits=DEFAULT_DIFFICULTY
    )
    
    # Tính block size
    block_size = len(json.dumps([coinbase_tx], default=str))
    
    logger.info("Genesis block created")
    
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
    """
    Thêm transactions vào block đã tồn tại.
    
    Lưu ý: Function này modify block in-place VÀ utxo_set.
    
    Args:
        block: Block cần thêm transactions
        transactions: Danh sách transactions
        utxo_set: UTXO set (sẽ được cập nhật)
        
    Returns:
        Tuple[Block, List[Tx]]: Block đã update và list các tx đã thêm
    """
    added_txs: List[Tx] = []
    
    for tx in transactions:
        try:
            # Kiểm tra block size limit
            if block.Blocksize > DEFAULT_BLOCK_SIZE_LIMIT:
                logger.warning("Block size limit reached")
                break
            
            # Verify và thêm transaction
            if not verify_transaction(tx, utxo_set):
                continue
            
            # Thêm vào block
            block.Txs.append(tx.to_dict())
            block.Txcount += 1
            block.Blocksize += len(json.dumps(tx.to_dict(), default=str))
            added_txs.append(tx)
            
            # Cập nhật UTXO set
            _update_utxo_set(tx, utxo_set)
            
            logger.debug(f"Added tx {tx.id()[:16]}... to block")
            
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            continue
    
    # Cập nhật Merkle root nếu có transactions mới
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
    """
    Cập nhật UTXO set sau khi thêm transaction.
    
    Actions:
    1. Xóa các outputs đã bị spend (inputs của tx)
    2. Thêm các outputs mới của tx
    """
    txid = tx.id()
    
    # Xóa spent outputs
    for tx_in in tx.tx_ins:
        if tx_in.prev_tx in utxo_set:
            utxo_set[tx_in.prev_tx].pop(tx_in.prev_index, None)
    
    # Thêm new outputs
    utxo_set[txid] = {}
    for i, tx_out in enumerate(tx.tx_outs):
        utxo_set[txid][i] = {
            'amount': tx_out.amount,
            'script_pubkey': tx_out.script_pubkey
        }
