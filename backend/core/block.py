class Block:
    def __init__(self, Height, Blocksize, Blockheader, Txcount, Txs):
        self.Height = Height
        self.Blocksize = Blocksize
        self.Blockheader = Blockheader
        self.Txcount = Txcount
        self.Txs = Txs
    
    def to_dict(self):
        """Convert block to dictionary for serialization"""
        return {
            'Height': self.Height,
            'Blocksize': self.Blocksize,
            'Blockheader': self.Blockheader.__dict__ if hasattr(self.Blockheader, '__dict__') else self.Blockheader,
            'Txcount': self.Txcount,
            'Txs': self.Txs
        }