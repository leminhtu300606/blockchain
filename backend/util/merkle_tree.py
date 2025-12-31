import hashlib
import math
from typing import List

class MerkleTree:
    def __init__(self, data_list: List[str]):
        self.leaves = data_list
        self.tree = []
        self._build_tree()

    def _build_tree(self):
        if not self.leaves:
            self.tree = [['0' * 64]]
            return

        # Ensure even number of leaves by duplicating the last one if needed
        current_layer = self.leaves[:]
        if len(current_layer) % 2 != 0:
            current_layer.append(current_layer[-1])

        self.tree = [current_layer]

        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer), 2):
                left = current_layer[i]
                right = current_layer[i+1]
                # Double SHA256 matches Bitcoin standard
                combined = left + right
                hash_val = hashlib.sha256(hashlib.sha256(bytes.fromhex(combined)).digest()).digest().hex()
                next_layer.append(hash_val)
            
            # Prepare for next level
            if len(next_layer) > 1 and len(next_layer) % 2 != 0:
                next_layer.append(next_layer[-1])
            
            self.tree.append(next_layer)
            current_layer = next_layer

    def get_root(self) -> str:
        if not self.tree:
             return '0' * 64
        return self.tree[-1][0]

    def get_proof(self, index: int) -> List[dict]:
        """
        Generate Merkle Proof for a given leaf index.
        Returns a list of dicts: {'data': hash, 'position': 'left'|'right'}
        """
        if index >= len(self.leaves) or index < 0:
            return []

        proof = []
        layer_index = index
        
        # Iterate through layers (excluding root)
        for layer in self.tree[:-1]:
            is_right_child = (layer_index % 2 == 1)
            sibling_index = layer_index - 1 if is_right_child else layer_index + 1
            
            if sibling_index < len(layer):
                proof.append({
                    'data': layer[sibling_index],
                    'position': 'left' if is_right_child else 'right'
                })
            
            layer_index //= 2
            
        return proof

    @staticmethod
    def verify_proof(leaf: str, proof: List[dict], root: str) -> bool:
        current_hash = leaf
        
        for item in proof:
            sibling = item['data']
            if item['position'] == 'left':
                combined = sibling + current_hash
            else:
                combined = current_hash + sibling
                
            current_hash = hashlib.sha256(hashlib.sha256(bytes.fromhex(combined)).digest()).digest().hex()
            
        return current_hash == root
