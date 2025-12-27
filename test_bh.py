import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from core.blockheader import BlockHeader
    print(f"Successfully imported BlockHeader from {BlockHeader.__module__}")
    
    bh = BlockHeader(version=1, previous_block_hash="0"*64, merkle_root="0"*64)
    print(f"Instantiated BlockHeader object.")
    
    if hasattr(bh, 'calculate_target'):
        print("SUCCESS: bh has attribute 'calculate_target'")
        print(f"Method object: {bh.calculate_target}")
    else:
        print("FAILURE: bh does NOT have attribute 'calculate_target'")
        
    import inspect
    print(f"File location: {inspect.getfile(BlockHeader)}")
    
except Exception as e:
    print(f"Error during diagnostic: {e}")
