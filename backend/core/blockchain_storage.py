import json
import os
from pathlib import Path

class BlockchainStorage:
    def __init__(self, filename='blockchain_data.json'):
        """
        Initialize blockchain storage.
        
        Args:
            filename (str): Name of the file to store blockchain data
        """
        # Create data directory if it doesn't exist
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)
        
        self.filepath = self.data_dir / filename
        self.chain = self.load_chain()
    
    def load_chain(self):
        """Load blockchain data from file."""
        try:
            if self.filepath.exists():
                with open(self.filepath, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        return []
    
    def save_chain(self):
        """Save blockchain data to file."""
        with open(self.filepath, 'w') as f:
            json.dump(self.chain, f, indent=2)
    
    def add_block(self, block_data):
        """
        Add a new block to the blockchain.
        
        Args:
            block_data (dict): Block data to add
        """
        if not isinstance(self.chain, list):
            self.chain = []
        
        self.chain.append(block_data)
        self.save_chain()
    
    def get_chain(self):
        """Get the entire blockchain."""
        return self.chain
    
    def get_latest_block(self):
        """Get the latest block in the blockchain."""
        if not self.chain:
            return None
        return self.chain[-1]
    
    def clear_chain(self):
        """Clear the blockchain (for testing purposes)."""
        self.chain = []
        self.save_chain()
        return True
