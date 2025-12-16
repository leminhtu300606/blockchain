import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.block import Block
from core.blockheader import BlockHeader
from core.Tx import Tx, TxIn, TxOut, Script
from database.database import BlockchainDB
from util.util import hash256
import time

ZERO_HASH = "0" * 64
VERSION = 1

class Blockchain:
    def __init__(self):
        self.GenesisBlock()

    def write_on_disk(self, block):
        """Write block to the blockchain database"""
        blockchainDB = BlockchainDB()
        blockchainDB.write(block)
        print(f"Block {block.get('Height', 'unknown')} added to the blockchain")

    def fetch_last_block (self): 
        blockchainDB = BlockchainDB ()
        return blockchainDB.lastBlock()

        
    def GenesisBlock(self):
        BlockHeight = 0
        previousblockhash = ZERO_HASH
        self.addBlock(BlockHeight, previousblockhash)
        
    def create_coinbase_tx(self, block_height):
        """
        Create a coinbase transaction (the first transaction in a block that rewards the miner).
        
        Args:
            block_height (int): The height of the block containing this transaction
            
        Returns:
            Tx: A coinbase transaction
        """

        halvings = block_height // 210000
        subsidy = 50 * (10**8)  # 50 BTC in satoshis
        reward = subsidy >> halvings  # Right shift for halving
        coinbase_data = f"Block {block_height} reward".encode('utf-8')
        script_sig = Script([
            block_height.to_bytes(4, 'little'),  # Block height as per BIP34
            len(coinbase_data).to_bytes(1, 'little'),
            coinbase_data
        ])
        
        tx_in = TxIn(
            prev_tx='0' * 64,     # 32 bytes of zeros for coinbase
            prev_index=0xffffffff,  # Special index for coinbase
            script_sig=script_sig,
            sequence=0xffffffff    # Default sequence number
        )
        script_pubkey = Script([
            'OP_DUP',
            'OP_HASH160',
            '00' * 20,  # Placeholder for the miner's pubkey hash
            'OP_EQUALVERIFY',
            'OP_CHECKSIG'
        ])
        
        tx_out = TxOut(amount=reward, script_pubkey=script_pubkey)
        
        # Create and return the transaction
        coinbase_tx = Tx(
            version=1,
            tx_ins=[tx_in],
            tx_outs=[tx_out],
            locktime=0  # Locktime is 0 for coinbase transactions
        )
        
        print(f"Created coinbase transaction for block {block_height} with reward: {reward/1e8} BTC")
        return coinbase_tx

    def addBlock(self, BlockHeight, prevBlockHash):
        """Add a new block to the blockchain"""
        timestamp = int(time.time())
        
        # Create coinbase transaction
        coinbase_tx = self.create_coinbase_tx(BlockHeight)
        
        # For now, we'll just use the coinbase transaction
        # In a real implementation, you would include other transactions here
        transactions = [coinbase_tx]
        
        # Calculate merkle root from transactions
        # This is a simplified version - in reality, you'd need to build a merkle tree
        tx_hashes = [tx.id() for tx in transactions]
        merkleRoot = hash256("".join(tx_hashes).encode()).hex()
        
        # Set the mining difficulty (simplified)
        bits = 'ffff001f'
        
        # Create and mine the block header
        blockheader = BlockHeader(VERSION, prevBlockHash, merkleRoot, timestamp, bits)
        blockheader.mine()
        
        # Create the block
        block = Block(
            Height=BlockHeight,
            Blocksize=0,  # This would be calculated from the actual block size
            Blockheader=blockheader,
            Txcount=len(transactions),
            Txs=[tx.to_dict() for tx in transactions]  # Convert transactions to dict for serialization
        )
        
        # Write the block to disk
        self.write_on_disk(block.to_dict())

    def main (self): 
        while True: 
            lastBlock = self.fetch_last_block()
            BlockHeight = lastBlock ["Height"] + 1
            prevBlockHash = lastBlock['Blockheader']['blockhash']
            self.addBlock(BlockHeight,prevBlockHash)
        

if __name__ == "__main__":
    print("Initializing blockchain...")
    blockchain = Blockchain()
    blockchain.main()