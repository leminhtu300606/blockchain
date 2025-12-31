"""
BlockHeader Module - Bitcoin Block Header Implementation

Block header chứa metadata của block và là phần được hash để mining.
Module này cung cấp class BlockHeader với chức năng:
- Serialize header theo format Bitcoin
- Mining (tìm nonce thỏa mãn difficulty)
- Calculate block hash

Cấu trúc Block Header (80 bytes):
┌──────────────────────────────────────────┐
│ Version (4 bytes)                        │
├──────────────────────────────────────────┤
│ Previous Block Hash (32 bytes)           │
├──────────────────────────────────────────┤
│ Merkle Root (32 bytes)                   │
├──────────────────────────────────────────┤
│ Timestamp (4 bytes)                      │
├──────────────────────────────────────────┤
│ Bits / Difficulty Target (4 bytes)       │
├──────────────────────────────────────────┤
│ Nonce (4 bytes)                          │
└──────────────────────────────────────────┘
"""
import time
import logging
from typing import Optional

from util.util import hash256


# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Default difficulty (dễ, cho testing)
DEFAULT_BITS = '1d00ffff'

# Mining progress report interval
MINING_REPORT_INTERVAL = 100000  # Báo cáo mỗi 100k hashes


# =============================================================================
# BLOCKHEADER CLASS
# =============================================================================

class BlockHeader:
    """
    Bitcoin Block Header - Metadata và proof-of-work của block.
    
    Block header là phần quan trọng nhất của block:
    - Chứa hash của block trước (tạo chain)
    - Chứa merkle root (commit tất cả transactions)
    - Chứa nonce (proof-of-work)
    
    Mining Process:
    1. Serialize header với nonce = 0
    2. Hash bằng double SHA-256
    3. Nếu hash < target: thành công!
    4. Nếu không: tăng nonce và lặp lại
    
    Attributes:
        version: Block version (1 hoặc 2)
        previous_block_hash: Hash của block trước (64 hex chars)
        merkle_root: Merkle root của transactions (64 hex chars)
        timestamp: Unix timestamp khi tạo block
        bits: Difficulty target dạng compact (8 hex chars)
        nonce: Giá trị tìm được khi mining (0 - 4,294,967,295)
        block_hash: Hash của header sau khi mine xong
    """
    
    __slots__ = [
        'version', 'previous_block_hash', 'merkle_root',
        'timestamp', 'bits', 'nonce', 'block_hash',
        '_header_prefix'  # Cache cho mining optimization
    ]
    
    def __init__(
        self, 
        version: int, 
        previous_block_hash: str, 
        merkle_root: str, 
        timestamp: Optional[int] = None, 
        bits: Optional[str] = None
    ):
        """
        Khởi tạo Block Header.
        
        Args:
            version: Block version number (thường là 1)
            previous_block_hash: Hash của block trước (64 hex chars)
            merkle_root: Merkle root của tất cả transactions
            timestamp: Unix timestamp, mặc định là thời điểm hiện tại
            bits: Difficulty target dạng compact, mặc định '1d00ffff'
        """
        self.version = version
        self.previous_block_hash = previous_block_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp or int(time.time())
        self.bits = bits or DEFAULT_BITS
        self.nonce = 0
        self.block_hash: Optional[str] = None
        
        # Pre-compute header prefix (không đổi trong quá trình mining)
        self._header_prefix: Optional[str] = None
    
    # =========================================================================
    # CALCULATION METHODS
    # =========================================================================
    
    def calculate_target(self) -> int:
        """
        Tính toán target numerical từ compact bits.
        """
        return self.bits_to_target(self.bits)

    # =========================================================================
    # MINING METHODS
    # =========================================================================
    
    def mine(self) -> str:
        """
        Mining block - Multi-threaded version.
        """
        logger.info("Starting block mining (multi-core)...")
        start_time = time.time()
        
        target = self.calculate_target()
        header_prefix = self._serialize_prefix()
        
        # Determine number of processes (leave 1 core free)
        import multiprocessing
        num_processes = max(1, multiprocessing.cpu_count() - 1)
        
        # Chunk size for each process
        chunk_size = 1_000_000
        max_nonce = 4_294_967_295
        
        found_nonce = None
        found_hash = None
        
        with multiprocessing.Pool(processes=num_processes) as pool:
            # Create tasks specific ranges for each worker
            # We submit batches to avoid creating too many tasks
            
            ctx = multiprocessing.get_context('spawn') # Safer for Windows usually, but let's trust default or 'spawn'
            
            # Simple approach: Each worker takes a Step
            # worker i checks nonces: i, i+step, i+2*step...
            # But Python mp is easier with distinct ranges
            
            results = []
            for i in range(num_processes):
                # We simply let workers run randomized or stepped ranges.
                # Simplest for this demo: 
                # Worker 0: 0 - 1B
                # Worker 1: 1B - 2B ...
                r_start = i * (max_nonce // num_processes)
                r_end = (i + 1) * (max_nonce // num_processes)
                results.append(pool.apply_async(_mine_worker, (header_prefix, target, r_start, r_end)))
            
            try:
                # Wait for FIRST success
                while True:
                    all_done = True
                    for res in results:
                        if not res.ready():
                            all_done = False
                            continue
                        
                        val = res.get()
                        if val: # Found!
                            found_nonce, found_hash = val
                            pool.terminate()
                            break
                    
                    if found_nonce is not None:
                        break
                        
                    if all_done:
                        break
                    
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pool.terminate()
                
        if found_nonce is not None:
            self.nonce = found_nonce
            self.block_hash = found_hash
            elapsed = time.time() - start_time
            hashrate = self.nonce / elapsed if elapsed > 0 else 0
            
            logger.info(f"Block mined successfully!")
            logger.info(f"  Hash: {self.block_hash}")
            logger.info(f"  Nonce: {self.nonce}")
            logger.info(f"  Time: {elapsed:.2f}s")
            logger.info(f"  Hashrate (effective): {hashrate:.0f} H/s")
            
            return self.block_hash
            
        return None

def _mine_worker(header_prefix, target, start_nonce, end_nonce):
    """Standalone worker function for multiprocessing."""
    nonce = start_nonce
    # Optimization: local variable access is faster
    import hashlib
    
    # Pre-parse prefix to bytes
    prefix_bytes = bytes.fromhex(header_prefix)
    
    while nonce < end_nonce:
        # Construct header: prefix + nonce (4 bytes little-endian)
        # Note: Optimization - manual byte concatenation
        header = prefix_bytes + nonce.to_bytes(4, 'little')
        
        # Double SHA256
        # digest() returns bytes, simpler to compare integers if we convert
        h1 = hashlib.sha256(header).digest()
        h2 = hashlib.sha256(h1).digest()
        
        # Convert to int - big-endian because hex string is big-endian representation of the number?
        # Bitcoin hash check: interpreted as little-endian number? 
        # Actually: 
        # hash_hex = h2[::-1].hex() 
        # hash_int = int(hash_hex, 16)
        # target is calculated as int 
        
        # Optimization: Compare bytes directly?
        # Target is large integer.
        # Let's stick to standard flow for correctness first
        
        hash_hex = h2[::-1].hex()
        if int(hash_hex, 16) < target:
            return nonce, hash_hex
            
        nonce += 1
        
        # Check cancellation? (Hard in simple loop without IPC)
        # We rely on Process.terminate() from main
        
        pass # end while
        
    return None
    

    
    @staticmethod
    def bits_to_target(bits: str) -> int:
        """
        Chuyển đổi bits (compact format) thành target number.
        
        Bits format (4 bytes hex): [exponent][coefficient]
        Target = coefficient * 2^(8*(exponent-3))
        
        Example: bits = '1d00ffff'
        - exponent = 0x1d (29)
        - coefficient = 0x00ffff
        - target = 0x00ffff * 2^(8*(29-3)) = 0x00ffff * 2^208
        """
        bits_bytes = bytes.fromhex(bits)
        exponent = bits_bytes[0]
        coefficient = int.from_bytes(bits_bytes[1:], 'big')
        return coefficient * 2**(8*(exponent - 3))

    @staticmethod
    def target_to_bits(target: int) -> str:
        """
        Chuyển đổi target number thành bits (compact format).
        """
        s = format(target, 'x')
        if len(s) % 2 != 0:
            s = '0' + s
        
        target_bytes = bytes.fromhex(s)
        
        # Nếu byte đầu >= 0x80, cần thêm 1 byte zero phía trước để tránh số âm
        if target_bytes[0] >= 0x80:
            target_bytes = b'\x00' + target_bytes
            
        exponent = len(target_bytes)
        coefficient = target_bytes[:3]
        
        # Kết quả là 1 byte exponent + 3 bytes coefficient
        return exponent.to_bytes(1, 'big').hex() + coefficient.hex()
    
    # =========================================================================
    # SERIALIZATION METHODS
    # =========================================================================
    
    def _serialize_prefix(self) -> str:
        """
        Serialize phần header KHÔNG bao gồm nonce.
        
        Dùng để optimization mining - chỉ compute 1 lần,
        sau đó append nonce mỗi iteration.
        
        Format (76 bytes = 152 hex chars):
        - Version: 4 bytes
        - Previous block hash: 32 bytes
        - Merkle root: 32 bytes
        - Timestamp: 4 bytes
        - Bits: 4 bytes
        
        Returns:
            str: Header prefix dạng hex
        """
        # Version (4 bytes, little-endian)
        version_hex = self.version.to_bytes(4, 'little').hex()
        
        # Previous block hash (32 bytes, little-endian)
        prev_hash = bytes.fromhex(self.previous_block_hash)[::-1].hex()
        
        # Merkle root (32 bytes, little-endian)
        merkle = bytes.fromhex(self.merkle_root)[::-1].hex()
        
        # Timestamp (4 bytes, little-endian)
        timestamp_hex = self.timestamp.to_bytes(4, 'little').hex()
        
        # Bits (4 bytes, little-endian)
        bits_hex = bytes.fromhex(self.bits)[::-1].hex()
        
        return version_hex + prev_hash + merkle + timestamp_hex + bits_hex
    
    def serialize(self) -> str:
        """
        Serialize toàn bộ header bao gồm nonce.
        
        Tổng: 80 bytes = 160 hex chars
        
        Returns:
            str: Full header dạng hex
        """
        header_prefix = self._serialize_prefix()
        nonce_hex = self.nonce.to_bytes(4, 'little').hex()
        return header_prefix + nonce_hex
    
    def to_dict(self) -> dict:
        """
        Chuyển đổi header thành dictionary.
        
        Dùng cho JSON serialization và lưu vào database.
        """
        return {
            'version': self.version,
            'previous_block_hash': self.previous_block_hash,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'bits': self.bits,
            'nonce': self.nonce,
            'blockhash': self.block_hash
        }
    
    def __repr__(self) -> str:
        return (
            f"BlockHeader(version={self.version}, "
            f"prev_hash={self.previous_block_hash[:16]}..., "
            f"nonce={self.nonce})"
        )
