import os
import json
from datetime import datetime

class BaseDB: 
    def __init__(self):
        self.basepath = os.path.join('..', '..', 'data')
        # Create data directory if it doesn't exist
        if not os.path.exists(self.basepath):
            os.makedirs(self.basepath)
        self.filename = 'blockchain_data'  # Using .txt extension for better compatibility
        self.filepath = os.path.abspath(os.path.join(self.basepath, self.filename))

    def read(self):
        if not os.path.exists(self.filepath):
            print(f"File {self.filepath} not found, creating new blockchain...")
            return []
            
        try:
            blocks = []
            current_block = {}
            with open(self.filepath, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith('Block'):
                        if current_block:  # Save previous block if exists
                            blocks.append(current_block)
                        current_block = {'Block': line.split(' ')[1]}
                    elif ':' in line and current_block is not None:
                        key, value = line.split(':', 1)
                        current_block[key.strip()] = value.strip()
                
                # Add the last block
                if current_block:
                    blocks.append(current_block)
            
            return blocks
            
        except Exception as e:
            print(f"Error reading {self.filepath}: {e}")
            return []

    def write(self, block_data):
        try:
            # Convert block data to the required text format
            formatted_block = []
            formatted_block.append(f"Block {block_data.get('Height', '0')}")
            
            # Format timestamp if it exists
            timestamp = block_data.get('Blockheader', {}).get('timestamp')
            if timestamp:
                dt = datetime.fromtimestamp(int(timestamp))
                formatted_block.append(f"Timestamp: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Add block hash
            if 'Blockheader' in block_data and 'blockhash' in block_data['Blockheader']:
                formatted_block.append(f"Hash: {block_data['Blockheader']['blockhash']}")
            
            # Add previous block hash
            if 'Blockheader' in block_data and 'previous_block_hash' in block_data['Blockheader']:
                formatted_block.append(f"Previous Hash: {block_data['Blockheader']['previous_block_hash']}")
            
            # Add transaction count
            formatted_block.append(f"Transactions: {block_data.get('Txcount', 0)}")
            
            # Add difficulty bits if available
            if 'Blockheader' in block_data and 'bits' in block_data['Blockheader']:
                formatted_block.append(f"Bits: {block_data['Blockheader']['bits']}")
            
            # Add nonce if available
            if 'Blockheader' in block_data and 'nonce' in block_data['Blockheader']:
                formatted_block.append(f"Nonce: {block_data['Blockheader']['nonce']}")
            
            # Add a separator line
            formatted_block.append('\n')
            
            # Write to file (append mode to add new blocks)
            with open(self.filepath, 'a') as file:
                file.write('\n'.join(formatted_block) + '\n')
                
        except Exception as e:
            print(f"Error writing to {self.filepath}: {e}")

class BlockchainDB(BaseDB):
    def __init__(self):
        super().__init__()
    
    def lastBlock(self):
        blocks = self.read()
        if blocks:
            # Return the last block with proper structure
            last = blocks[-1]
            # Convert back to the expected format
            return {
                'Height': int(last['Block']),
                'Blockheader': {
                    'blockhash': last.get('Hash', ''),
                    'previous_block_hash': last.get('Previous Hash', ''),
                    'timestamp': int(datetime.strptime(last['Timestamp'], '%Y-%m-%d %H:%M:%S').timestamp())
                    if 'Timestamp' in last else 0,
                    'bits': last.get('Bits', '1d00ffff'),
                    'nonce': int(last.get('Nonce', 0))
                },
                'Txcount': int(last.get('Transactions', 0))
            }
        return None
