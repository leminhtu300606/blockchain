"""
Database Module - Lưu trữ dữ liệu Blockchain

Module này cung cấp các class để đọc/ghi blockchain data:
- BaseDB: Base class với các phương thức cơ bản
- BlockchainDB: Class chuyên biệt cho blockchain operations

Tính năng:
- File-based storage (text format)
- Caching để giảm I/O
- Path handling với pathlib
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any


# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_FILENAME = 'blockchain.json'
DEFAULT_BITS = '1d00ffff'


# =============================================================================
# BASE DATABASE CLASS
# =============================================================================

class BaseDB:
    """
    Base Database Class - Xử lý đọc/ghi file cơ bản.
    
    Cung cấp:
    - Path management với pathlib (cross-platform)
    - Caching để giảm I/O operations
    - Text-based storage format
    
    Attributes:
        basepath: Thư mục chứa data files
        filename: Tên file (không có extension)
        filepath: Đường dẫn đầy đủ đến file
        _cache: Cache dữ liệu đã đọc
        _cache_valid: Cache có còn hợp lệ không
    """
    
    def __init__(self, filename: str = DEFAULT_FILENAME):
        """
        Khởi tạo BaseDB.
        
        Args:
            filename: Tên file data (default: 'blockchain_data')
        """
        # Sử dụng pathlib cho cross-platform path handling
        # Data folder nằm ở cùng cấp với backend folder
        self.basepath = Path(__file__).parent.parent.parent / 'data'
        
        # Tạo thư mục nếu chưa tồn tại
        self.basepath.mkdir(parents=True, exist_ok=True)
        
        self.filename = filename
        self.filepath = self.basepath / filename
        
        # Caching
        self._cache: Optional[List[Dict]] = None
        self._cache_valid = False
        
        logger.debug(f"Database initialized: {self.filepath}")

    def read(self) -> List[Dict[str, Any]]:
        """
        Đọc dữ liệu từ file JSON.
        """
        if self._cache_valid and self._cache is not None:
            return self._cache
        
        if not self.filepath.exists():
            return []
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self._cache = data
                self._cache_valid = True
                return data
        except Exception as e:
            logger.error(f"Error reading database: {e}")
            return []

    def write_all(self, data: List[Dict[str, Any]]) -> bool:
        """
        Ghi toàn bộ dữ liệu vào file.
        """
        try:
            with open(self.filepath, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4)
            self._invalidate_cache()
            return True
        except Exception as e:
            logger.error(f"Error writing to database: {e}")
            return False

    def write(self, block_data: Dict[str, Any]) -> bool:
        """
        Ghi một block mới vào cuối danh sách.
        """
        blocks = self.read()
        blocks.append(block_data)
        return self.write_all(blocks)
    
    def _invalidate_cache(self) -> None:
        """Đánh dấu cache không còn hợp lệ."""
        self._cache_valid = False
        logger.debug("Cache invalidated")


# =============================================================================
# BLOCKCHAIN DATABASE CLASS
# =============================================================================

class BlockchainDB(BaseDB):
    """
    Blockchain Database - Chuyên biệt cho blockchain operations.
    
    Kế thừa BaseDB và thêm các method:
    - lastBlock(): Lấy block cuối cùng
    - get_block_by_height(): Lấy block theo height
    - clear(): Xóa toàn bộ blockchain
    """
    
    def __init__(self):
        """Khởi tạo BlockchainDB với default filename."""
        super().__init__(filename=DEFAULT_FILENAME)
    
    def lastBlock(self) -> Optional[Dict[str, Any]]:
        """
        Lấy block cuối cùng trong blockchain.
        
        Dùng để:
        - Lấy previous_block_hash khi tạo block mới
        - Xác định block height tiếp theo
        
        Returns:
            Dict chứa block data với format chuẩn, hoặc None nếu blockchain rỗng
        """
        blocks = self.read()
        
        if not blocks:
            logger.info("Blockchain is empty")
            return None
        
        # Lấy block cuối
        last = blocks[-1]
        
        # Chuyển đổi về format chuẩn
        return self._normalize_block(last)
    
    def get_block_by_height(self, height: int) -> Optional[Dict[str, Any]]:
        """
        Lấy block theo height.
        
        Args:
            height: Block height (0-indexed)
            
        Returns:
            Dict chứa block data, hoặc None nếu không tìm thấy
        """
        blocks = self.read()
        
        for block in blocks:
            if int(block.get('Block', -1)) == height:
                return self._normalize_block(block)
        
        logger.warning(f"Block at height {height} not found")
        return None
    
    def get_transactions_by_address(self, address: str) -> List[Dict[str, Any]]:
        """
        Tìm tất cả giao dịch liên quan đến một địa chỉ.
        """
        blocks = self.read()
        history = []
        
        for block in blocks:
            height = int(block.get('Block', 0))
            timestamp = block.get('Timestamp', '')
            
            for tx in block.get('Txs', []):
                # Search in outputs
                is_relevant = False
                for output in tx.get('outputs', []):
                    if address in output:
                        is_relevant = True
                        break
                
                # Search in inputs (if not coinbase)
                if not is_relevant and tx.get('type') != 'Coinbase':
                    for inp in tx.get('inputs', []):
                        # This part is harder because we don't store sender address directly in DB 
                        # but we can look for address hash in input markers if we had more info
                        pass
                
                if is_relevant:
                    history.append({
                        'txid': tx['txid'],
                        'type': tx['type'],
                        'block_height': height,
                        'timestamp': timestamp,
                        'outputs': tx['outputs'],
                        'inputs': tx['inputs']
                    })
            
        return history

    def get_transaction_by_id(self, txid: str) -> Optional[Dict[str, Any]]:
        """
        Tìm giao dịch theo TXID.
        """
        blocks = self.read()
        for block in blocks:
            for tx in block.get('Txs', []):
                if tx['txid'] == txid or tx['txid'].startswith(txid):
                    return {
                        'txid': tx['txid'],
                        'type': tx['type'],
                        'block_height': int(block.get('Block', 0)),
                        'timestamp': block.get('Timestamp', ''),
                        'outputs': tx['outputs'],
                        'inputs': tx['inputs']
                    }
        return None
    
    def clear(self) -> bool:
        """
        Xóa toàn bộ blockchain (dùng cho testing).
        
        Returns:
            bool: True nếu xóa thành công
        """
        try:
            if self.filepath.exists():
                self.filepath.unlink()  # Xóa file
            
            self._invalidate_cache()
            logger.info("Blockchain database cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            return False
    
    def _normalize_block(self, raw_block: Dict[str, Any]) -> Dict[str, Any]:
        """
        Chuẩn hóa block data về format chuẩn.
        
        Chuyển đổi từ text file format sang program format.
        
        Args:
            raw_block: Block data đọc từ file
            
        Returns:
            Dict với format chuẩn
        """
        # Parse timestamp
        timestamp = 0
        if 'Timestamp' in raw_block:
            try:
                dt = datetime.strptime(raw_block['Timestamp'], '%Y-%m-%d %H:%M:%S')
                timestamp = int(dt.timestamp())
            except ValueError:
                logger.warning(f"Could not parse timestamp: {raw_block['Timestamp']}")
        
        return {
            'Height': int(raw_block.get('Block', 0)),
            'Blockheader': {
                'blockhash': raw_block.get('Hash', ''),
                'previous_block_hash': raw_block.get('Previous Hash', ''),
                'timestamp': timestamp,
                'bits': raw_block.get('Bits', DEFAULT_BITS),
                'nonce': int(raw_block.get('Nonce', 0))
            },
            'Txcount': int(raw_block.get('Transactions', 0)),
            'Txs': raw_block.get('Txs', [])
        }


class BalanceDB(BaseDB):
    """
    Balance Database - Quản lý số dư và lịch sử biến động.
    Lưu trữ vào file balance_ledger.txt
    """
    
    def __init__(self):
        super().__init__(filename='balance_ledger')

    def record_change(self, address: str, block_height: int, change: int, final_balance: int) -> bool:
        """
        Ghi lại một biến động số dư.
        Format: Address | Block | Change | Balance
        """
        line = f"{address} | {block_height} | {change} | {final_balance}\n"
        try:
            with open(self.filepath, 'a', encoding='utf-8') as f:
                f.write(line)
            return True
        except Exception as e:
            logger.error(f"Error recording balance change: {e}")
            return False

    def get_history(self, address: str) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử biến động số dư của một địa chỉ.
        """
        history = []
        if not self.filepath.exists():
            return history

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if address in line:
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) == 4 and parts[0] == address:
                            history.append({
                                'block': int(parts[1]),
                                'change': int(parts[2]),
                                'balance': int(parts[3])
                            })
            return history
        except Exception as e:
            logger.error(f"Error reading balance history: {e}")
            return []

    def get_latest_balance(self, address: str) -> int:
        """
        Lấy số dư cuối cùng của một địa chỉ.
        """
        history = self.get_history(address)
        if not history:
            return 0
        return history[-1]['balance']
