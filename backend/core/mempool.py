"""
Memory Pool (Mempool) implementation for storing unconfirmed transactions.
"""
import time
from typing import Dict, List, Optional, Set, Tuple
from .Tx import Tx
from .transaction_verifier import TransactionVerifier

class Mempool:
    """
    Memory Pool (Mempool) stores unconfirmed transactions that are waiting to be included in a block.
    
    Transactions are stored in the mempool until they are included in a block or expire.
    """
    
    def __init__(self, max_size: int = 10000, tx_expiry: int = 3600):
        """
        Initialize the mempool.
        
        Args:
            max_size: Maximum number of transactions the mempool can hold
            tx_expiry: Time in seconds after which a transaction expires from the mempool
        """
        self.transactions: Dict[str, Dict] = {}  # txid -> {tx: Tx, timestamp: float, fee: int}
        self.max_size = max_size
        self.tx_expiry = tx_expiry
        self.utxo_set = {}  # Simplified UTXO set for conflict detection
        
    def calculate_fee(self, tx: Tx) -> int:
        """
        Calculate the transaction fee by comparing input and output amounts.
        
        Args:
            tx: The transaction to calculate the fee for
            
        Returns:
            int: The transaction fee in satoshis, or -1 if the transaction is invalid
        """
        if tx.is_coinbase():
            return 0  # Coinbase transactions have no fee
            
        # Calculate total input amount
        input_sum = 0
        for tx_in in tx.tx_ins:
            # Check if the input is in the UTXO set
            if tx_in.prev_tx not in self.utxo_set or tx_in.prev_index not in self.utxo_set[tx_in.prev_tx]:
                return -1  # Invalid input
            input_sum += self.utxo_set[tx_in.prev_tx][tx_in.prev_index]['amount']
        
        # Calculate total output amount
        output_sum = sum(tx_out.amount for tx_out in tx.tx_outs)
        
        # Fee is the difference between inputs and outputs
        fee = input_sum - output_sum
        
        # Return -1 if the fee is negative (invalid transaction)
        return fee if fee >= 0 else -1
    
    def add_transaction(self, tx: Tx, txid: str, fee: Optional[int] = None) -> bool:
        """
        Add a transaction to the mempool if it's valid and doesn't conflict with existing transactions.
        
        Args:
            tx: The transaction to add
            txid: The transaction ID
            fee: Optional transaction fee in satoshis. If None, it will be calculated automatically
            
        Returns:
            bool: True if the transaction was added, False otherwise
        """
        # Check if mempool is full
        if len(self.transactions) >= self.max_size:
            return False
            
        # Check if transaction already exists in mempool
        if txid in self.transactions:
            return False
            
        # Verify the transaction
        if not self._is_valid_transaction(tx, txid):
            return False
            
        # Check for conflicts with existing transactions
        if self._has_conflicts(tx):
            return False
        
        # Calculate fee if not provided
        if fee is None:
            fee = self.calculate_fee(tx)
            if fee < 0:  # Invalid fee (negative or invalid transaction)
                return False
        
        # Add transaction to mempool
        self.transactions[txid] = {
            'tx': tx,
            'timestamp': time.time(),
            'fee': fee,
            'size': len(str(tx))  # Approximate size in bytes
        }
        
        # Update UTXO set (for conflict detection)
        self._update_utxo_set(tx, txid)
        
        return True
    
    def get_transaction(self, txid: str) -> Optional[Tx]:
        """Get a transaction from the mempool by its ID."""
        if txid in self.transactions:
            return self.transactions[txid]['tx']
        return None
    
    def remove_transaction(self, txid: str) -> bool:
        """Remove a transaction from the mempool."""
        if txid in self.transactions:
            # Remove from UTXO set
            self._remove_from_utxo_set(self.transactions[txid]['tx'])
            # Remove from transactions
            del self.transactions[txid]
            return True
        return False
    
    def get_transactions_for_block(self, max_size: int = 1000000) -> List[Tx]:
        """
        Get transactions from the mempool to include in a new block.
        
        Args:
            max_size: Maximum total size of transactions to return (in bytes)
            
        Returns:
            List of transactions sorted by fee rate (highest first)
        """
        # Clean up expired transactions
        self._cleanup()
        
        # Sort transactions by fee rate (fee per byte)
        sorted_txs = sorted(
            self.transactions.values(),
            key=lambda x: x['fee'] / max(1, x['size']),  # Avoid division by zero
            reverse=True
        )
        
        # Select transactions that fit in the block
        selected_txs = []
        total_size = 0
        
        for tx_data in sorted_txs:
            if total_size + tx_data['size'] <= max_size:
                selected_txs.append(tx_data['tx'])
                total_size += tx_data['size']
            else:
                break
                
        return selected_txs
    
    def _is_valid_transaction(self, tx: Tx, txid: str) -> bool:
        """Check if a transaction is valid."""
        # Basic validation
        if not tx.tx_ins or not tx.tx_outs:
            return False
            
        # Check for double spends in the mempool
        if self._has_double_spends(tx):
            return False
            
        # Verify the transaction using the transaction verifier
        # Note: In a real implementation, you would also check against the blockchain's UTXO set
        return TransactionVerifier.verify_transaction(tx, self.utxo_set)
    
    def _has_conflicts(self, tx: Tx) -> bool:
        """Check if a transaction conflicts with existing transactions in the mempool."""
        for tx_in in tx.tx_ins:
            # Check if any input is already spent in the mempool
            if tx_in.prev_tx in self.utxo_set and tx_in.prev_index in self.utxo_set[tx_in.prev_tx]:
                return True
        return False
    
    def _has_double_spends(self, tx: Tx) -> bool:
        """Check if a transaction is trying to spend outputs that are already spent."""
        for tx_in in tx.tx_ins:
            # If the input is not in our UTXO set, it's either already spent or invalid
            if tx_in.prev_tx not in self.utxo_set or tx_in.prev_index not in self.utxo_set[tx_in.prev_tx]:
                return True
        return False
    
    def _update_utxo_set(self, tx: Tx, txid: str) -> None:
        """Update the mempool's UTXO set with a new transaction."""
        # Remove spent outputs
        for tx_in in tx.tx_ins:
            if tx_in.prev_tx in self.utxo_set and tx_in.prev_index in self.utxo_set[tx_in.prev_tx]:
                del self.utxo_set[tx_in.prev_tx][tx_in.prev_index]
                
        # Add new outputs
        for i, tx_out in enumerate(tx.tx_outs):
            if txid not in self.utxo_set:
                self.utxo_set[txid] = {}
            self.utxo_set[txid][i] = {
                'amount': tx_out.amount,
                'script_pubkey': tx_out.script_pubkey
            }
    
    def _remove_from_utxo_set(self, tx: Tx) -> None:
        """Remove a transaction's outputs from the UTXO set."""
        # This is used when a transaction is removed from the mempool
        # In a real implementation, you would need to handle this more carefully
        # to handle transactions that spend from other transactions in the mempool
        for tx_in in tx.tx_ins:
            if tx_in.prev_tx in self.utxo_set and tx_in.prev_index in self.utxo_set[tx_in.prev_tx]:
                del self.utxo_set[tx_in.prev_tx][tx_in.prev_index]
    
    def _cleanup(self) -> None:
        """Remove expired transactions from the mempool."""
        current_time = time.time()
        expired_txs = [
            txid for txid, tx_data in self.transactions.items()
            if current_time - tx_data['timestamp'] > self.tx_expiry
        ]
        
        for txid in expired_txs:
            self.remove_transaction(txid)
    
    def get_size(self) -> int:
        """Get the current number of transactions in the mempool."""
        return len(self.transactions)
    
    def clear(self) -> None:
        """Clear all transactions from the mempool."""
        self.transactions.clear()
        self.utxo_set.clear()
        
    def remove_spent_transactions(self, block_txs: List[Tx]) -> List[str]:
        """
        Remove transactions from the mempool that spend outputs already spent by transactions in the new block.
        
        Args:
            block_txs: List of transactions in the newly added block
            
        Returns:
            List of transaction IDs that were removed from the mempool
        """
        removed_txids = []
        
        # First, collect all input outpoints that are spent in the new block
        spent_outpoints = set()
        for tx in block_txs:
            for tx_in in tx.tx_ins:
                # Skip coinbase transactions as they don't spend any outputs
                if tx.is_coinbase():
                    continue
                    
                # Add the outpoint (prev_tx + prev_index) to the spent set
                outpoint = (tx_in.prev_tx, tx_in.prev_index)
                spent_outpoints.add(outpoint)
        
        # Now check each transaction in the mempool for conflicts
        for txid in list(self.transactions.keys()):
            tx = self.transactions[txid]['tx']
            
            # Check if any input of this mempool transaction is spent by the new block
            for tx_in in tx.tx_ins:
                outpoint = (tx_in.prev_tx, tx_in.prev_index)
                if outpoint in spent_outpoints:
                    # This transaction is now invalid as its input is already spent
                    self.remove_transaction(txid)
                    removed_txids.append(txid)
                    break  # No need to check other inputs of this transaction
        
        return removed_txids

# Global mempool instance
mempool = Mempool()
