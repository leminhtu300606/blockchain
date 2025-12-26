import sys
import os
import time

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from core.blockchain import Blockchain
from core.mempool import mempool
from core.Tx import Tx, TxIn, TxOut, Script
from core.database.database import BalanceDB

def test_balance_evolution():
    print("Initializing test blockchain...")
    bc = Blockchain()
    bal_db = BalanceDB()
    
    test_addr = "test_wallet_address_123"
    initial_bal = bal_db.get_latest_balance(test_addr)
    print(f"Initial balance for {test_addr}: {initial_bal} sats")
    
    # Create a mock transaction to this address
    tx_out = TxOut(amount=5000, script_pubkey=Script(['OP_DUP', 'OP_HASH160', test_addr, 'OP_EQUALVERIFY', 'OP_CHECKSIG']))
    tx = Tx(version=1, tx_ins=[TxIn(prev_tx="0"*64, prev_index=0)], tx_outs=[tx_out], locktime=0)
    
    print(f"Adding transaction to mempool...")
    mempool.transactions[tx.id()] = {'tx': tx, 'timestamp': time.time(), 'fee': 0, 'size': 200}
    mempool._fee_heap.append((0, tx.id()))
    
    print("Mining block...")
    last_block = bc.fetch_last_block()
    bc.add_block(last_block['Height'] + 1, last_block['Blockheader']['blockhash'])
    
    new_bal = bal_db.get_latest_balance(test_addr)
    print(f"New balance for {test_addr}: {new_bal} sats")
    
    history = bal_db.get_history(test_addr)
    print(f"History entries found: {len(history)}")
    for entry in history:
        print(f"  Block #{entry['block']}: {entry['change']} change -> {entry['balance']} total")

    if new_bal == initial_bal + 5000:
        print("\nSUCCESS: Balance history tracked correctly!")
    else:
        print("\nFAILURE: Balance mismatch.")

if __name__ == "__main__":
    test_balance_evolution()
