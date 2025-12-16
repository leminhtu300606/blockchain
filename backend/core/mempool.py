"""
Mempool Module - Bộ nhớ đệm cho các transaction chưa được xác nhận

Mempool (Memory Pool) lưu trữ các transaction đang chờ được đưa vào block:
- Nhận transaction mới từ network
- Xác thực transaction trước khi thêm vào
- Cung cấp transaction cho miners để đóng block
- Tự động dọn dẹp transaction hết hạn

Tính năng tối ưu:
- Priority queue để lấy transaction có fee cao nhất nhanh chóng
- UTXO tracking để phát hiện double-spend
- Automatic expiry cleanup
"""
import time
import heapq
import logging
from typing import Dict, List, Optional, Set, Tuple, Any

from .Tx import Tx
from .transaction_verifier import TransactionVerifier


# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_MAX_SIZE = 10000       # Số transaction tối đa trong mempool
DEFAULT_TX_EXPIRY = 3600       # Thời gian hết hạn (giây) - 1 giờ
DEFAULT_BLOCK_SIZE = 1000000   # Block size limit (bytes) - 1MB


# =============================================================================
# MEMPOOL CLASS
# =============================================================================

class Mempool:
    """
    Memory Pool - Lưu trữ và quản lý các transaction chưa được confirm.
    
    Workflow:
    1. Nhận transaction mới → add_transaction()
    2. Xác thực transaction (format, signature, double-spend)
    3. Lưu vào mempool với metadata (timestamp, fee)
    4. Miner lấy transaction → get_transactions_for_block()
    5. Sau khi block được mine → remove_transaction()
    
    Cấu trúc dữ liệu:
    - transactions: Dict[txid → {tx, timestamp, fee, size}]
    - _fee_heap: Priority queue để lấy tx có fee rate cao nhất
    - utxo_set: Theo dõi UTXO để phát hiện double-spend
    
    Attributes:
        transactions: Dictionary chứa tất cả transactions
        max_size: Số transaction tối đa
        tx_expiry: Thời gian hết hạn (giây)
        utxo_set: UTXO set cho conflict detection
    """
    
    def __init__(
        self, 
        max_size: int = DEFAULT_MAX_SIZE, 
        tx_expiry: int = DEFAULT_TX_EXPIRY
    ):
        """
        Khởi tạo Mempool.
        
        Args:
            max_size: Số transaction tối đa (default: 10,000)
            tx_expiry: Thời gian hết hạn transaction tính bằng giây (default: 1 giờ)
        """
        # Transaction storage: txid → transaction data
        self.transactions: Dict[str, Dict[str, Any]] = {}
        
        # Priority queue: (negative_fee_rate, txid)
        # Dùng negative vì Python heapq là min-heap
        self._fee_heap: List[Tuple[float, str]] = []
        
        # Configuration
        self.max_size = max_size
        self.tx_expiry = tx_expiry
        
        # UTXO set cho conflict detection
        # Format: {prev_tx_hash: {output_index: {amount, script_pubkey}}}
        self.utxo_set: Dict[str, Dict[int, Dict[str, Any]]] = {}
        
        logger.info(f"Mempool initialized: max_size={max_size}, expiry={tx_expiry}s")
    
    # =========================================================================
    # PUBLIC METHODS - Transaction Management
    # =========================================================================
    
    def add_transaction(
        self, 
        tx: Tx, 
        txid: str, 
        fee: Optional[int] = None
    ) -> bool:
        """
        Thêm transaction vào mempool.
        
        Quá trình xác thực:
        1. Kiểm tra mempool đầy chưa
        2. Kiểm tra transaction đã tồn tại chưa
        3. Xác thực transaction (format, signature)
        4. Kiểm tra conflict (double-spend)
        5. Tính fee nếu chưa có
        6. Thêm vào mempool và priority queue
        
        Args:
            tx: Transaction object cần thêm
            txid: Transaction ID
            fee: Transaction fee (satoshis). Nếu None, sẽ tự tính
            
        Returns:
            bool: True nếu thêm thành công, False nếu thất bại
        """
        # 1. Kiểm tra mempool đầy
        if len(self.transactions) >= self.max_size:
            logger.warning(f"Mempool full, rejecting tx {txid[:16]}...")
            return False
            
        # 2. Kiểm tra đã tồn tại
        if txid in self.transactions:
            logger.debug(f"Transaction {txid[:16]}... already in mempool")
            return False
            
        # 3. Xác thực transaction
        if not self._is_valid_transaction(tx, txid):
            logger.warning(f"Invalid transaction {txid[:16]}...")
            return False
            
        # 4. Kiểm tra conflicts
        if self._has_conflicts(tx):
            logger.warning(f"Transaction {txid[:16]}... conflicts with existing tx")
            return False
        
        # 5. Tính fee nếu cần
        if fee is None:
            fee = self._calculate_fee(tx)
            if fee < 0:
                logger.warning(f"Transaction {txid[:16]}... has invalid fee")
                return False
        
        # 6. Tính size (approximate)
        tx_size = self._estimate_size(tx)
        
        # 7. Lưu transaction
        self.transactions[txid] = {
            'tx': tx,
            'timestamp': time.time(),
            'fee': fee,
            'size': tx_size
        }
        
        # 8. Thêm vào priority queue (negative fee rate cho max-heap behavior)
        fee_rate = -fee / max(1, tx_size)  # satoshis per byte (negative)
        heapq.heappush(self._fee_heap, (fee_rate, txid))
        
        # 9. Cập nhật UTXO set
        self._update_utxo_set(tx, txid)
        
        logger.info(f"Added tx {txid[:16]}... to mempool (fee={fee}, size={tx_size})")
        return True
    
    def get_transaction(self, txid: str) -> Optional[Tx]:
        """
        Lấy transaction từ mempool theo ID.
        
        Args:
            txid: Transaction ID cần tìm
            
        Returns:
            Tx object hoặc None nếu không tìm thấy
        """
        tx_data = self.transactions.get(txid)
        return tx_data['tx'] if tx_data else None
    
    def remove_transaction(self, txid: str) -> bool:
        """
        Xóa transaction khỏi mempool.
        
        Thường được gọi sau khi transaction đã được confirm trong block.
        
        Args:
            txid: Transaction ID cần xóa
            
        Returns:
            bool: True nếu xóa thành công
        """
        if txid not in self.transactions:
            return False
        
        tx = self.transactions[txid]['tx']
        
        # Xóa khỏi UTXO tracking
        self._remove_from_utxo_set(tx)
        
        # Xóa khỏi transactions
        del self.transactions[txid]
        
        # Note: Không cần xóa khỏi heap, sẽ được filter ra khi truy cập
        logger.debug(f"Removed tx {txid[:16]}... from mempool")
        return True
    
    def get_transactions_for_block(
        self, 
        max_size: int = DEFAULT_BLOCK_SIZE
    ) -> List[Tx]:
        """
        Lấy danh sách transactions để đưa vào block mới.
        
        Transactions được sắp xếp theo fee rate (cao → thấp) để maximize
        miner revenue. Chỉ lấy đủ transactions vừa với block size limit.
        
        Algorithm:
        1. Cleanup expired transactions
        2. Lấy từ priority queue theo thứ tự fee rate giảm dần
        3. Dừng khi đạt block size limit
        
        Args:
            max_size: Giới hạn tổng size của transactions (bytes)
            
        Returns:
            List[Tx]: Danh sách transactions đã sắp xếp
        """
        # Dọn dẹp transactions hết hạn
        self._cleanup_expired()
        
        selected_txs: List[Tx] = []
        total_size = 0
        
        # Rebuild heap với các transaction còn valid
        valid_heap: List[Tuple[float, str]] = []
        
        while self._fee_heap:
            fee_rate, txid = heapq.heappop(self._fee_heap)
            
            # Skip nếu transaction đã bị xóa
            if txid not in self.transactions:
                continue
            
            tx_data = self.transactions[txid]
            tx_size = tx_data['size']
            
            # Kiểm tra còn đủ chỗ không
            if total_size + tx_size <= max_size:
                selected_txs.append(tx_data['tx'])
                total_size += tx_size
            
            # Giữ lại trong heap cho block tiếp theo
            valid_heap.append((fee_rate, txid))
        
        # Khôi phục heap
        self._fee_heap = valid_heap
        heapq.heapify(self._fee_heap)
        
        logger.info(f"Selected {len(selected_txs)} txs for block (size={total_size})")
        return selected_txs
    
    def remove_confirmed_transactions(self, block_txs: List[Tx]) -> List[str]:
        """
        Xóa các transaction đã được confirm trong block.
        
        Khi một block mới được thêm vào blockchain, cần:
        1. Xóa các transaction trong block khỏi mempool
        2. Xóa các transaction conflict (double-spend)
        
        Args:
            block_txs: Danh sách transactions trong block mới
            
        Returns:
            List[str]: Danh sách txid đã bị xóa
        """
        removed_txids: List[str] = []
        
        # Thu thập tất cả outpoints đã bị spend trong block
        spent_outpoints: Set[Tuple[str, int]] = set()
        
        for tx in block_txs:
            # Skip coinbase
            if tx.is_coinbase():
                continue
            
            for tx_in in tx.tx_ins:
                outpoint = (tx_in.prev_tx, tx_in.prev_index)
                spent_outpoints.add(outpoint)
        
        # Xóa các transaction conflict
        for txid in list(self.transactions.keys()):
            tx = self.transactions[txid]['tx']
            
            # Kiểm tra conflict
            for tx_in in tx.tx_ins:
                outpoint = (tx_in.prev_tx, tx_in.prev_index)
                if outpoint in spent_outpoints:
                    self.remove_transaction(txid)
                    removed_txids.append(txid)
                    break
        
        logger.info(f"Removed {len(removed_txids)} conflicting txs from mempool")
        return removed_txids
    
    # =========================================================================
    # QUERY METHODS
    # =========================================================================
    
    def get_size(self) -> int:
        """Trả về số lượng transactions trong mempool."""
        return len(self.transactions)
    
    def get_total_fees(self) -> int:
        """Trả về tổng fee của tất cả transactions."""
        return sum(data['fee'] for data in self.transactions.values())
    
    def clear(self) -> None:
        """Xóa toàn bộ mempool (dùng cho testing)."""
        self.transactions.clear()
        self._fee_heap.clear()
        self.utxo_set.clear()
        logger.info("Mempool cleared")
    
    # =========================================================================
    # PRIVATE HELPER METHODS
    # =========================================================================
    
    def _calculate_fee(self, tx: Tx) -> int:
        """
        Tính transaction fee = sum(inputs) - sum(outputs).
        
        Returns:
            int: Fee (satoshis), hoặc -1 nếu invalid
        """
        if tx.is_coinbase():
            return 0
        
        # Tính tổng inputs
        input_sum = 0
        for tx_in in tx.tx_ins:
            utxo = self.utxo_set.get(tx_in.prev_tx, {}).get(tx_in.prev_index)
            if not utxo:
                return -1  # Input không tồn tại
            input_sum += utxo['amount']
        
        # Tính tổng outputs
        output_sum = sum(tx_out.amount for tx_out in tx.tx_outs)
        
        # Fee = inputs - outputs
        fee = input_sum - output_sum
        return fee if fee >= 0 else -1
    
    def _estimate_size(self, tx: Tx) -> int:
        """
        Ước tính size của transaction (bytes).
        
        Đây là phiên bản đơn giản. Trong thực tế cần serialize chính xác.
        """
        # Rough estimate: 10 bytes overhead + 150 bytes/input + 34 bytes/output
        base_size = 10
        input_size = len(tx.tx_ins) * 150
        output_size = len(tx.tx_outs) * 34
        return base_size + input_size + output_size
    
    def _is_valid_transaction(self, tx: Tx, txid: str) -> bool:
        """
        Xác thực transaction cơ bản.
        
        Kiểm tra:
        - Có inputs và outputs
        - Không có double-spend trong mempool
        - Signature hợp lệ
        """
        # Phải có inputs và outputs
        if not tx.tx_ins or (not tx.is_coinbase() and not tx.tx_outs):
            return False
        
        # Kiểm tra double-spend
        if self._has_double_spends(tx):
            return False
        
        # Xác thực với TransactionVerifier
        return TransactionVerifier.verify_transaction(tx, self.utxo_set)
    
    def _has_conflicts(self, tx: Tx) -> bool:
        """
        Kiểm tra transaction có conflict với mempool không.
        
        Conflict xảy ra khi một input đã được spend bởi transaction khác.
        """
        for tx_in in tx.tx_ins:
            # Nếu UTXO đã bị spend trong mempool → conflict
            if tx_in.prev_tx in self.utxo_set:
                if tx_in.prev_index in self.utxo_set[tx_in.prev_tx]:
                    return True
        return False
    
    def _has_double_spends(self, tx: Tx) -> bool:
        """
        Kiểm tra transaction có đang cố double-spend không.
        
        Double-spend: Cố gắng spend một output đã được spend.
        """
        for tx_in in tx.tx_ins:
            # Input phải tồn tại trong UTXO set
            if tx_in.prev_tx not in self.utxo_set:
                return True
            if tx_in.prev_index not in self.utxo_set[tx_in.prev_tx]:
                return True
        return False
    
    def _update_utxo_set(self, tx: Tx, txid: str) -> None:
        """
        Cập nhật UTXO set sau khi thêm transaction.
        
        - Xóa các outputs đã bị spend (inputs của tx)
        - Thêm các outputs mới của tx
        """
        # Xóa spent outputs
        for tx_in in tx.tx_ins:
            if tx_in.prev_tx in self.utxo_set:
                self.utxo_set[tx_in.prev_tx].pop(tx_in.prev_index, None)
        
        # Thêm new outputs
        self.utxo_set[txid] = {}
        for i, tx_out in enumerate(tx.tx_outs):
            self.utxo_set[txid][i] = {
                'amount': tx_out.amount,
                'script_pubkey': tx_out.script_pubkey
            }
    
    def _remove_from_utxo_set(self, tx: Tx) -> None:
        """
        Xóa các outputs của transaction khỏi UTXO set.
        
        Gọi khi remove transaction khỏi mempool.
        """
        txid = tx.id()
        self.utxo_set.pop(txid, None)
    
    def _cleanup_expired(self) -> None:
        """
        Xóa các transactions đã hết hạn khỏi mempool.
        
        Transaction hết hạn nếu:
        - current_time - tx_timestamp > tx_expiry
        """
        current_time = time.time()
        
        expired_txids = [
            txid for txid, data in self.transactions.items()
            if current_time - data['timestamp'] > self.tx_expiry
        ]
        
        for txid in expired_txids:
            self.remove_transaction(txid)
            logger.debug(f"Expired tx {txid[:16]}... removed")
        
        if expired_txids:
            logger.info(f"Cleaned up {len(expired_txids)} expired transactions")


# =============================================================================
# GLOBAL MEMPOOL INSTANCE
# =============================================================================

# Singleton instance cho toàn ứng dụng
mempool = Mempool()
