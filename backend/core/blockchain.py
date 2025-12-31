"""
Blockchain Module - Quản lý chuỗi khối Bitcoin

Module chính điều phối toàn bộ blockchain:
- Tạo Genesis block
- Thêm block mới
- Mining blocks
- Đọc/ghi từ database

Workflow:
1. Khởi tạo → Tạo Genesis block (nếu chưa có)
2. Mining loop: Tạo block mới → Mine → Ghi vào DB
3. Repeat

Usage:
    blockchain = Blockchain()
    blockchain.main()  # Start mining loop
"""
import sys
import os
import time
import logging
from typing import Optional, List, Dict, Any

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.block import Block
from core.blockheader import BlockHeader
from core.Tx import Tx, TxIn, TxOut, Script
from core.database.database import BlockchainDB, BalanceDB
from core.mempool import mempool
from util.util import hash256


# =============================================================================
# LOGGING SETUP
# =============================================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

ZERO_HASH = "0" * 64                    # 32 bytes zeros (hex)
VERSION = 1                              # Block version
INITIAL_SUBSIDY = 50 * (10 ** 8)        # 50 BTC in satoshis
HALVING_INTERVAL = 210_000               # Blocks between halvings
# Độ khó hố đen (Cực dễ cho Genesis - Admin khởi tạo)
GENESIS_DIFFICULTY = '20ffffff' 

# Độ khó tiêu chuẩn (Cho User - Cần tính toán thực sự)
DEFAULT_DIFFICULTY = '1e00ffff' 

# Các hằng số điều chỉnh
DIFFICULTY_ADJUSTMENT_INTERVAL = 10      # Điều chỉnh sau mỗi 10 blocks
TARGET_BLOCK_TIME = 60                   # Mục tiêu 1 phút/block
MAX_TARGET = 0x0000ffff00000000000000000000000000000000000000000000000000000000


# =============================================================================
# BLOCKCHAIN CLASS
# =============================================================================

class Blockchain:
    """
    Bitcoin Blockchain - Quản lý chuỗi khối.
    
    Responsibilities:
    - Duy trì state của blockchain
    - Tạo blocks mới với transactions
    - Mining blocks
    - Persist blocks vào database
    
    Attributes:
        db: Database instance để đọc/ghi blocks
        
    Example:
        blockchain = Blockchain()
        # Genesis block được tạo tự động trong __init__
        blockchain.main()  # Bắt đầu mining loop
    """
    
    def __init__(self):
        """
        Khởi tạo Blockchain.
        
        Nếu database rỗng, tự động tạo Genesis block.
        """
        self.db = BlockchainDB()
        self.balance_db = BalanceDB()
        
        # Kiểm tra và tạo Genesis block nếu cần
        last_block = self.db.lastBlock()
        if last_block is None:
            logger.info("No blocks found. Creating Genesis block...")
            self._create_genesis_block()
        else:
            logger.info(f"Blockchain loaded. Last block height: {last_block['Height']}")
    
    # =========================================================================
    # GENESIS BLOCK
    # =========================================================================
    
    def _create_genesis_block(self) -> None:
        """
        Tạo Genesis Block (block đầu tiên).
        
        Genesis block có:
        - Height = 0
        - Previous hash = zeros
        - Chứa coinbase transaction
        """
        logger.info("Creating Genesis block...")
        self.add_block(
            block_height=0, 
            previous_hash=ZERO_HASH,
            bits=GENESIS_DIFFICULTY
        )
        logger.info("Genesis block created successfully")
    
    # =========================================================================
    # BLOCK REWARD CALCULATION
    # =========================================================================
    
    def calculate_block_reward(self, block_height: int) -> int:
        """
        Tính block reward dựa trên height.
        
        Bitcoin halving: Reward giảm 50% mỗi 210,000 blocks
        
        Timeline:
        - Blocks 0 - 209,999: 50 BTC
        - Blocks 210,000 - 419,999: 25 BTC
        - Blocks 420,000 - 629,999: 12.5 BTC
        - ...
        
        Args:
            block_height: Chiều cao của block
            
        Returns:
            int: Block reward in satoshis
        """
        halvings = block_height // HALVING_INTERVAL
        
        # Sau 64 halvings, reward = 0 (do right shift)
        if halvings >= 64:
            return 0
        
        reward = INITIAL_SUBSIDY >> halvings
        return reward
    
    # =========================================================================
    # COINBASE TRANSACTION
    # =========================================================================
    
    def create_coinbase_tx(self, block_height: int) -> Tx:
        """
        Tạo Coinbase Transaction.
        
        Coinbase transaction là transaction đầu tiên trong block:
        - Không có input thực (prev_tx = zeros)
        - Tạo ra tiền mới (block reward)
        - ScriptSig chứa block height (BIP34)
        
        Args:
            block_height: Height của block chứa transaction này
            
        Returns:
            Tx: Coinbase transaction object
        """
        # Tính reward (có thể cộng thêm fees từ mempool)
        reward = self.calculate_block_reward(block_height)
        
        # Tạo ScriptSig chứa block height và message
        coinbase_message = f"Block {block_height} reward".encode('utf-8')
        script_sig = Script([
            block_height.to_bytes(4, 'little'),  # Block height (BIP34)
            len(coinbase_message).to_bytes(1, 'little'),
            coinbase_message
        ])
        
        # Coinbase input (special: prev_tx = zeros)
        tx_in = TxIn(
            prev_tx=ZERO_HASH,
            prev_index=0xffffffff,  # Special index for coinbase
            script_sig=script_sig,
            sequence=0xffffffff
        )
        
        # Miner's P2PKH script (placeholder address)
        script_pubkey = Script([
            'OP_DUP',
            'OP_HASH160',
            '00' * 20,  # Placeholder: thay bằng miner's pubkey hash thực
            'OP_EQUALVERIFY',
            'OP_CHECKSIG'
        ])
        
        # Output gửi reward cho miner
        tx_out = TxOut(amount=reward, script_pubkey=script_pubkey)
        
        # Tạo transaction
        coinbase_tx = Tx(
            version=1,
            tx_ins=[tx_in],
            tx_outs=[tx_out],
            locktime=0
        )
        
        logger.info(
            f"Created coinbase for block {block_height}: "
            f"reward = {reward / 10**8:.8f} BTC"
        )
        
        return coinbase_tx
    
    # =========================================================================
    # DIFFICULTY ADJUSTMENT
    # =========================================================================
    
    def calculate_next_bits(self, last_block: Dict[str, Any]) -> str:
        """
        Tính toán difficulty (bits) cho block tiếp theo.
        
        Nếu đến chu kỳ điều chỉnh:
        - Tính thời gian thực tế để mine 10 blocks cuối
        - So sánh với thời gian mong đợi (10 * TARGET_BLOCK_TIME)
        - Điều chỉnh target (bits) tương ứng (nhưng không vượt quá MAX_TARGET)
        """
        height = last_block['Height']
        current_bits = last_block['Blockheader']['bits']
        
        # Chỉ điều chỉnh sau mỗi DIFFICULTY_ADJUSTMENT_INTERVAL blocks
        if (height + 1) % DIFFICULTY_ADJUSTMENT_INTERVAL != 0:
            return current_bits
            
        # Lấy block bắt đầu chu kỳ
        first_block_height = height - (DIFFICULTY_ADJUSTMENT_INTERVAL - 1)
        first_block = self.db.get_block_by_height(first_block_height)
        
        if not first_block:
            return current_bits
            
        # Tính thời gian thực tế
        actual_time = last_block['Blockheader']['timestamp'] - first_block['Blockheader']['timestamp']
        expected_time = DIFFICULTY_ADJUSTMENT_INTERVAL * TARGET_BLOCK_TIME
        
        # Tránh biến động quá lớn (max 4x hoặc min 0.25x)
        if actual_time < expected_time // 4:
            actual_time = expected_time // 4
        if actual_time > expected_time * 4:
            actual_time = expected_time * 4
            
        # Điều chỉnh target
        current_target = BlockHeader.bits_to_target(current_bits)
        new_target = (current_target * actual_time) // expected_time
        
        # Giới hạn target
        if new_target > MAX_TARGET:
            new_target = MAX_TARGET
            
        new_bits = BlockHeader.target_to_bits(new_target)
        logger.info(f"Difficulty adjusted: {current_bits} -> {new_bits} (Actual: {actual_time}s, Expected: {expected_time}s)")
        
        return new_bits
    
    # =========================================================================
    # ADD BLOCK
    # =========================================================================
    
    def add_block(self, block_height: int, previous_hash: str, bits: Optional[str] = None) -> None:
        """
        Tạo và thêm block mới vào blockchain.
        
        Process:
        1. Tạo coinbase transaction
        2. Thu thập transactions từ mempool (TODO)
        3. Tính Merkle root
        4. Tạo block header
        5. Mining (tìm nonce)
        6. Ghi vào database
        
        Args:
            block_height: Height cho block mới
            previous_hash: Hash của block trước
        """
        logger.info(f"Creating block {block_height}...")
        
        timestamp = int(time.time())
        
        # 1. Tạo coinbase transaction
        coinbase_tx = self.create_coinbase_tx(block_height)
        
        # 2. Thu thập transactions từ mempool
        mempool_txs = mempool.get_transactions_for_block()
        transactions = [coinbase_tx] + mempool_txs
        
        # 3. Tính Merkle root
        tx_hashes = [tx.id() for tx in transactions]
        merkle_root = self._calculate_merkle_root(tx_hashes)
        
        # 4. Xác định difficulty (bits)
        if not bits:
            last_block = self.db.lastBlock()
            bits = self.calculate_next_bits(last_block) if last_block else DEFAULT_DIFFICULTY
        
        # 5. Tạo block header
        blockheader = BlockHeader(
            version=VERSION,
            previous_block_hash=previous_hash,
            merkle_root=merkle_root,
            timestamp=timestamp,
            bits=bits
        )
        
        # 5. Mining
        logger.info(f"Mining block {block_height}...")
        blockheader.mine()
        
        # 6. Tạo block object
        block = Block(
            Height=block_height,
            Blocksize=0,  # Simplified
            Blockheader=blockheader,
            Txcount=len(transactions),
            Txs=[tx.to_dict() for tx in transactions]
        )
        
        # 7. Ghi vào database
        self._write_block(block)
        
        logger.info(f"Block {block_height} added successfully")
    
    def _calculate_merkle_root(self, tx_hashes: List[str]) -> str:
        """
        Tính Merkle root từ danh sách transaction hashes.
        
        Simplified version - trong production nên dùng module merkle.py
        """
        if not tx_hashes:
            return ZERO_HASH
        
        # Nối tất cả hashes và hash kết quả
        combined = "".join(tx_hashes)
        return hash256(combined.encode()).hex()
    
    def _write_block(self, block: Block) -> None:
        """
        Ghi block vào database và cập nhật sổ cái số dư.
        """
        block_dict = block.to_dict()
        self.db.write(block_dict)
        
        # Cập nhật số dư cho từng giao dịch trong block
        block_height = block.Height
        for tx_dict in block_dict.get('Txs', []):
            # 1. Xử lý Outputs (Tăng số dư)
            for tx_out in tx_dict.get('tx_outs', []):
                addr = "unknown"
                script = tx_out.get('script_pubkey', [])
                if isinstance(script, list) and len(script) >= 3 and script[0] == 'OP_DUP':
                    addr = script[2]
                
                amount = tx_out.get('amount', 0)
                current_bal = self.balance_db.get_latest_balance(addr)
                self.balance_db.record_change(addr, block_height, amount, current_bal + amount)

            # 2. Xử lý Inputs (Giảm số dư - Skip coinbase)
            if not tx_dict.get('is_coinbase'):
                for tx_in in tx_dict.get('tx_ins', []):
                    prev_tx_id = tx_in.get('prev_tx')
                    prev_index = tx_in.get('prev_index')
                    
                    # Tìm transaction gốc để biết ai là người trả tiền
                    prev_tx = self.db.get_transaction_by_id(prev_tx_id)
                    
                    if prev_tx:
                        prev_outputs = prev_tx.get('outputs', [])
                        if prev_index < len(prev_outputs):
                            spent_output = prev_outputs[prev_index]
                            
                            # Lấy địa chỉ và số tiền
                            addr = "unknown"
                            script = spent_output.get('script_pubkey', [])
                            # Trích xuất address từ P2PKH script (OP_DUP, OP_HASH160, <ADDR>, ...)
                            if isinstance(script, list) and len(script) >= 3 and script[0] == 'OP_DUP':
                                addr = script[2]
                                
                            amount = spent_output.get('amount', 0)
                            
                            # Trừ tiền
                            current_bal = self.balance_db.get_latest_balance(addr)
                            new_bal = current_bal - amount
                            self.balance_db.record_change(addr, block_height, -amount, new_bal)
                            logger.info(f"Deducted {amount} from {addr} (Tx: {prev_tx_id})")
                        else:
                             logger.error(f"Invalid output index {prev_index} in tx {prev_tx_id}")
                    else:
                        # Transaction chưa được index hoặc không tìm thấy (có thể do chưa đồng bộ)
                        # Trong thực tế cần xử lý kỹ hơn, ở đây ta log warning
                        logger.warning(f"Could not find previous tx {prev_tx_id}")

        logger.info(f"Block {block_height} written to database and ledger updated")
    
    # =========================================================================
    # FETCH BLOCKS
    # =========================================================================
    
    def fetch_last_block(self) -> Optional[Dict[str, Any]]:
        """
        Lấy block cuối cùng từ database.
        
        Returns:
            Dict chứa block data, hoặc None nếu chain rỗng
        """
        return self.db.lastBlock()
    
    def get_chain_height(self) -> int:
        """
        Lấy chiều cao hiện tại của blockchain.
        
        Returns:
            int: Block height của block cuối (0 nếu chỉ có genesis)
        """
        last_block = self.fetch_last_block()
        return last_block['Height'] if last_block else -1
    
    # =========================================================================
    # MAIN MINING LOOP
    # =========================================================================
    
    def main(self) -> None:
        """
        Main mining loop - Liên tục tạo blocks mới.
        
        Loop vô hạn:
        1. Lấy block cuối
        2. Tạo block tiếp theo
        3. Repeat
        
        Note: Trong production, cần:
        - Lấy transactions từ mempool
        - Xử lý block reorganization
        - Network communication
        """
        logger.info("Starting mining loop...")
        
        while True:
            try:
                # Lấy block cuối
                last_block = self.fetch_last_block()
                
                if last_block is None:
                    logger.error("No blocks in chain. This shouldn't happen.")
                    break
                
                # Tính toán cho block tiếp theo
                new_height = last_block['Height'] + 1
                prev_hash = last_block['Blockheader']['blockhash']
                
                # Tạo block mới
                self.add_block(new_height, prev_hash)
                
            except KeyboardInterrupt:
                logger.info("Mining stopped by user")
                break
                
            except Exception as e:
                logger.error(f"Error in mining loop: {e}")
                # Đợi một chút trước khi thử lại
                time.sleep(1)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("BITCOIN BLOCKCHAIN")
    print("=" * 60)
    
    logger.info("Initializing blockchain...")
    blockchain = Blockchain()
    
    logger.info("Starting main loop...")
    blockchain.main()