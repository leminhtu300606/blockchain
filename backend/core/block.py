"""
Block Module - Bitcoin Block Implementation

Block là container chứa:
- Block header (metadata + proof-of-work)
- Danh sách transactions

Cấu trúc Block:
┌─────────────────────────────────────────────┐
│ Block Header (80 bytes)                     │
│   - Version                                 │
│   - Previous Block Hash                     │
│   - Merkle Root                             │
│   - Timestamp                               │
│   - Bits (difficulty)                       │
│   - Nonce                                   │
├─────────────────────────────────────────────┤
│ Transaction Count (VarInt)                  │
├─────────────────────────────────────────────┤
│ Transactions                                │
│   - Coinbase (block reward)                 │
│   - Regular transactions                    │
└─────────────────────────────────────────────┘
"""
from typing import List, Dict, Any, Optional


class Block:
    """
    Bitcoin Block - Container cho transactions.
    
    Block chứa:
    - Header với metadata và proof-of-work
    - Danh sách transactions (coinbase first)
    
    Attributes:
        Height: Vị trí trong blockchain (0 = genesis)
        Blocksize: Kích thước tính bằng bytes
        Blockheader: BlockHeader object hoặc dict
        Txcount: Số lượng transactions
        Txs: Danh sách transactions (as dicts)
    """
    
    __slots__ = ['Height', 'Blocksize', 'Blockheader', 'Txcount', 'Txs']
    
    def __init__(
        self, 
        Height: int, 
        Blocksize: int, 
        Blockheader: Any, 
        Txcount: int, 
        Txs: List[Dict[str, Any]]
    ):
        """
        Khởi tạo Block.
        
        Args:
            Height: Block height (0-indexed)
            Blocksize: Size in bytes
            Blockheader: BlockHeader object hoặc dict
            Txcount: Number of transactions
            Txs: List of transactions as dicts
        """
        self.Height = Height
        self.Blocksize = Blocksize
        self.Blockheader = Blockheader
        self.Txcount = Txcount
        self.Txs = Txs
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Chuyển đổi block thành dictionary.
        
        Dùng cho JSON serialization và lưu vào database.
        
        Returns:
            dict: Block data
        """
        # Convert header to dict if it's an object
        if hasattr(self.Blockheader, 'to_dict'):
            header_dict = self.Blockheader.to_dict()
        elif hasattr(self.Blockheader, '__dict__'):
            header_dict = self.Blockheader.__dict__
        else:
            header_dict = self.Blockheader
        
        return {
            'Height': self.Height,
            'Blocksize': self.Blocksize,
            'Blockheader': header_dict,
            'Txcount': self.Txcount,
            'Txs': self.Txs
        }
    
    def get_hash(self) -> Optional[str]:
        """
        Lấy block hash.
        
        Returns:
            str: Block hash hoặc None
        """
        if hasattr(self.Blockheader, 'block_hash'):
            return self.Blockheader.block_hash
        elif isinstance(self.Blockheader, dict):
            return self.Blockheader.get('blockhash') or self.Blockheader.get('block_hash')
        return None
    
    def get_merkle_root(self) -> Optional[str]:
        """
        Lấy merkle root.
        
        Returns:
            str: Merkle root hoặc None
        """
        if hasattr(self.Blockheader, 'merkle_root'):
            return self.Blockheader.merkle_root
        elif isinstance(self.Blockheader, dict):
            return self.Blockheader.get('merkle_root')
        return None
    
    def __repr__(self) -> str:
        block_hash = self.get_hash()
        hash_str = block_hash[:16] + '...' if block_hash else 'None'
        return f"Block(height={self.Height}, hash={hash_str}, txs={self.Txcount})"