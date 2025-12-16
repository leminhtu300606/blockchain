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

DEFAULT_FILENAME = 'blockchain_data'
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
        Đọc dữ liệu blockchain từ file.
        
        Format file:
            Block 0
            Timestamp: 2024-01-01 00:00:00
            Hash: abc123...
            Previous Hash: 000...
            Transactions: 1
            Bits: 1d00ffff
            Nonce: 12345
            
            Block 1
            ...
        
        Optimization:
        - Trả về cache nếu còn valid
        - Chỉ đọc file khi cần thiết
        
        Returns:
            List[Dict]: Danh sách blocks dưới dạng dictionaries
        """
        # Trả về cache nếu valid
        if self._cache_valid and self._cache is not None:
            logger.debug("Returning cached blockchain data")
            return self._cache
        
        # File chưa tồn tại
        if not self.filepath.exists():
            logger.info(f"Database file not found: {self.filepath}")
            logger.info("Returning empty blockchain (will be created)")
            return []
        
        try:
            blocks: List[Dict[str, Any]] = []
            current_block: Dict[str, Any] = {}
            
            with open(self.filepath, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    
                    # Dòng trống hoặc block mới
                    if not line:
                        continue
                    
                    # Bắt đầu block mới
                    if line.startswith('Block'):
                        # Lưu block trước (nếu có)
                        if current_block:
                            blocks.append(current_block)
                        
                        # Parse block number
                        parts = line.split(' ')
                        block_num = parts[1] if len(parts) > 1 else '0'
                        current_block = {'Block': block_num}
                    
                    # Parse key:value pairs
                    elif ':' in line and current_block:
                        key, value = line.split(':', 1)
                        current_block[key.strip()] = value.strip()
                
                # Lưu block cuối cùng
                if current_block:
                    blocks.append(current_block)
            
            # Update cache
            self._cache = blocks
            self._cache_valid = True
            
            logger.info(f"Loaded {len(blocks)} blocks from database")
            return blocks
            
        except Exception as e:
            logger.error(f"Error reading database: {e}")
            return []

    def write(self, block_data: Dict[str, Any]) -> bool:
        """
        Ghi một block mới vào file.
        
        Args:
            block_data: Dictionary chứa block data với format:
                {
                    'Height': 0,
                    'Blockheader': {
                        'timestamp': 1234567890,
                        'blockhash': 'abc...',
                        'previous_block_hash': '000...',
                        'bits': '1d00ffff',
                        'nonce': 12345
                    },
                    'Txcount': 1
                }
        
        Returns:
            bool: True nếu ghi thành công
        """
        try:
            # Chuẩn bị formatted block
            formatted_lines: List[str] = []
            
            # Block header
            block_height = block_data.get('Height', 0)
            formatted_lines.append(f"Block {block_height}")
            
            # Timestamp
            blockheader = block_data.get('Blockheader', {})
            timestamp = blockheader.get('timestamp')
            if timestamp:
                dt = datetime.fromtimestamp(int(timestamp))
                formatted_lines.append(f"Timestamp: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Block hash
            blockhash = blockheader.get('blockhash', blockheader.get('block_hash', ''))
            if blockhash:
                formatted_lines.append(f"Hash: {blockhash}")
            
            # Previous hash
            prev_hash = blockheader.get('previous_block_hash', '')
            if prev_hash:
                formatted_lines.append(f"Previous Hash: {prev_hash}")
            
            # Transaction count
            tx_count = block_data.get('Txcount', 0)
            formatted_lines.append(f"Transactions: {tx_count}")
            
            # Bits (difficulty)
            bits = blockheader.get('bits', DEFAULT_BITS)
            formatted_lines.append(f"Bits: {bits}")
            
            # Nonce
            nonce = blockheader.get('nonce', 0)
            formatted_lines.append(f"Nonce: {nonce}")
            
            # Dòng trống để phân cách blocks
            formatted_lines.append('')
            
            # Ghi vào file (append mode)
            with open(self.filepath, 'a', encoding='utf-8') as file:
                file.write('\n'.join(formatted_lines) + '\n')
            
            # Invalidate cache
            self._invalidate_cache()
            
            logger.info(f"Block {block_height} written to database")
            return True
                
        except Exception as e:
            logger.error(f"Error writing to database: {e}")
            return False
    
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
            'Txcount': int(raw_block.get('Transactions', 0))
        }
