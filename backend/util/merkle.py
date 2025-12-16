"""
Merkle Tree Module - Merkle Tree Implementation cho Bitcoin

Merkle Tree là cấu trúc dữ liệu dùng để:
- Commit tất cả transactions vào một hash duy nhất (Merkle Root)
- Chứng minh một transaction có trong block mà không cần download toàn bộ block

Cấu trúc Merkle Tree:
                    Root
                   /    \
                 H(AB)   H(CD)
                /    \   /    \
              H(A)  H(B) H(C)  H(D)
               |     |    |     |
              Tx1   Tx2  Tx3   Tx4

Function chính:
- calculate_merkle_root(): Tính Merkle root
- get_merkle_path(): Lấy proof path cho SPV verification
- verify_merkle_proof(): Xác minh proof
"""
import hashlib
from typing import List, Optional


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def double_sha256(data: bytes) -> bytes:
    """
    Tính double SHA-256 hash (chuẩn Bitcoin).
    
    Hash = SHA256(SHA256(data))
    
    Lý do dùng double:
    - Tăng cường bảo mật chống length extension attack
    - Chuẩn Bitcoin từ đầu
    
    Args:
        data: Dữ liệu cần hash
        
    Returns:
        bytes: 32-byte hash
    """
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


# =============================================================================
# MERKLE ROOT CALCULATION
# =============================================================================

def calculate_merkle_root(tx_hashes: List[str]) -> str:
    """
    Tính Merkle Root từ danh sách transaction hashes.
    
    Thuật toán:
    1. Nếu chỉ có 1 hash → đó là root
    2. Nếu số hash lẻ → duplicate hash cuối
    3. Ghép cặp và hash: H(hash[0] + hash[1]), H(hash[2] + hash[3]),...
    4. Lặp lại cho đến khi còn 1 hash
    
    Ví dụ với 4 transactions:
        Level 0: [H1, H2, H3, H4]
        Level 1: [H(H1+H2), H(H3+H4)]
        Level 2: [H(H12+H34)] ← Merkle Root
    
    Args:
        tx_hashes: Danh sách transaction hashes (hex strings, big-endian)
        
    Returns:
        str: Merkle root dưới dạng hex string (little-endian như Bitcoin)
    """
    if not tx_hashes:
        return ""
    
    # Chuyển đổi sang bytes (little-endian theo Bitcoin format)
    hashes = [bytes.fromhex(h)[::-1] for h in tx_hashes]
    
    # Build tree từ dưới lên
    while len(hashes) > 1:
        # Duplicate hash cuối nếu số lượng lẻ
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])
        
        # Hash từng cặp
        new_level: List[bytes] = []
        for i in range(0, len(hashes), 2):
            # Ghép 2 hash liền kề và double-hash
            combined = hashes[i] + hashes[i + 1]
            new_hash = double_sha256(combined)
            new_level.append(new_hash)
        
        hashes = new_level
    
    # Trả về dạng hex (big-endian để hiển thị)
    return hashes[0][::-1].hex() if hashes else ""


# =============================================================================
# MERKLE PROOF FUNCTIONS
# =============================================================================

def get_merkle_path(tx_hashes: List[str], tx_index: int) -> List[str]:
    """
    Lấy Merkle path (proof) cho một transaction.
    
    Merkle path chứa các hash "anh em" cần thiết để verify
    từ transaction hash lên đến root.
    
    Ví dụ: Để prove Tx2 (index=1):
        Path = [H1, H(H3+H4)]
        
        Verification:
        1. H(H1 + H2) = H12
        2. H(H12 + H34) = Root ✓
    
    Args:
        tx_hashes: Danh sách tất cả transaction hashes
        tx_index: Index của transaction cần prove (0-indexed)
        
    Returns:
        List[str]: Danh sách sibling hashes từ leaf lên root
    """
    if not tx_hashes or tx_index >= len(tx_hashes):
        return []
    
    # Chuyển sang bytes
    level = [bytes.fromhex(h)[::-1] for h in tx_hashes]
    path: List[str] = []
    index = tx_index
    
    while len(level) > 1:
        # Pad nếu cần
        if len(level) % 2 != 0:
            level.append(level[-1])
        
        # Xác định sibling
        if index % 2 == 0:
            # Transaction ở bên trái → sibling ở bên phải
            sibling = level[index + 1]
        else:
            # Transaction ở bên phải → sibling ở bên trái
            sibling = level[index - 1]
        
        # Thêm sibling vào path
        path.append(sibling[::-1].hex())
        
        # Build next level
        new_level: List[bytes] = []
        for i in range(0, len(level), 2):
            combined = level[i] + level[i + 1]
            new_level.append(double_sha256(combined))
        
        level = new_level
        index = index // 2
    
    return path


def verify_merkle_proof(
    tx_hash: str, 
    merkle_root: str, 
    merkle_path: List[str], 
    tx_index: int
) -> bool:
    """
    Xác minh Merkle proof cho một transaction.
    
    Quá trình verify:
    1. Bắt đầu với tx_hash
    2. Với mỗi hash trong path:
        - Nếu index bit = 0: current ở trái, sibling ở phải
        - Nếu index bit = 1: sibling ở trái, current ở phải
        - Hash ghép lại
    3. Kết quả cuối = merkle_root → VALID
    
    Args:
        tx_hash: Hash của transaction cần verify
        merkle_root: Merkle root mong đợi (từ block header)
        merkle_path: Danh sách sibling hashes (từ get_merkle_path)
        tx_index: Vị trí của transaction trong block
        
    Returns:
        bool: True nếu proof hợp lệ
    """
    if not tx_hash or not merkle_root:
        return False
    
    # Bắt đầu với tx hash
    current = bytes.fromhex(tx_hash)[::-1]
    
    for i, sibling_hex in enumerate(merkle_path):
        sibling = bytes.fromhex(sibling_hex)[::-1]
        
        # Bit thứ i của index xác định thứ tự ghép
        if (tx_index >> i) & 1:
            # Current ở bên phải
            current = double_sha256(sibling + current)
        else:
            # Current ở bên trái
            current = double_sha256(current + sibling)
    
    # So sánh với merkle root
    computed_root = current[::-1].hex()
    return computed_root == merkle_root


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MERKLE TREE DEMO")
    print("=" * 60)
    
    # Tạo mock transaction hashes (64 hex chars mỗi hash)
    tx_hashes = [
        "a" * 64,
        "b" * 64,
        "c" * 64,
        "d" * 64
    ]
    
    print(f"\n📋 Transactions ({len(tx_hashes)}):")
    for i, h in enumerate(tx_hashes):
        print(f"   Tx{i}: {h[:16]}...")
    
    # Tính Merkle root
    merkle_root = calculate_merkle_root(tx_hashes)
    print(f"\n🌳 Merkle Root: {merkle_root[:32]}...")
    
    # Lấy proof cho Tx0
    tx_index = 0
    merkle_path = get_merkle_path(tx_hashes, tx_index)
    print(f"\n📍 Merkle Path for Tx{tx_index}:")
    for i, h in enumerate(merkle_path):
        print(f"   Level {i}: {h[:16]}...")
    
    # Verify proof
    is_valid = verify_merkle_proof(
        tx_hash=tx_hashes[tx_index],
        merkle_root=merkle_root,
        merkle_path=merkle_path,
        tx_index=tx_index
    )
    print(f"\n✅ Proof Valid: {is_valid}")