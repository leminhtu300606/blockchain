"""
Transaction (Tx) Module - Bitcoin Transaction Implementation

Module này chứa các class cơ bản để xây dựng và xử lý Bitcoin transactions:
- Script: Lệnh script trong transaction (scriptSig, scriptPubKey)
- TxIn: Transaction input - tham chiếu đến output của transaction trước
- TxOut: Transaction output - định nghĩa số tiền và điều kiện chi tiêu
- Tx: Transaction đầy đủ với inputs, outputs và metadata

Tất cả các class sử dụng __slots__ để tối ưu bộ nhớ.
"""
import hashlib
from typing import List, Optional, Any, Union


# =============================================================================
# CONSTANTS - Các hằng số chuẩn Bitcoin
# =============================================================================

# Hash của transaction trống (dùng cho coinbase transaction)
COINBASE_PREV_TX = '0' * 64  # 32 bytes = 64 hex chars

# Previous index đặc biệt cho coinbase transaction  
COINBASE_PREV_INDEX = 0xffffffff

# Sequence number mặc định (không có RBF - Replace-By-Fee)
DEFAULT_SEQUENCE = 0xffffffff


# =============================================================================
# HELPER FUNCTIONS - Các hàm tiện ích dùng chung
# =============================================================================

def encode_varint(n: int) -> bytes:
    """
    Mã hóa số nguyên thành Variable Length Integer (VarInt).
    
    VarInt là định dạng nén của Bitcoin để lưu số nguyên:
    - 0-252: 1 byte
    - 253-65535: 0xfd + 2 bytes  
    - 65536-4294967295: 0xfe + 4 bytes
    - Lớn hơn: 0xff + 8 bytes
    
    Args:
        n: Số nguyên cần mã hóa
        
    Returns:
        bytes: VarInt đã mã hóa (little-endian)
    """
    if n < 0xfd:
        return n.to_bytes(1, 'little')
    elif n <= 0xffff:
        return b'\xfd' + n.to_bytes(2, 'little')
    elif n <= 0xffffffff:
        return b'\xfe' + n.to_bytes(4, 'little')
    else:
        return b'\xff' + n.to_bytes(8, 'little')


# =============================================================================
# SCRIPT CLASS - Bitcoin Script
# =============================================================================

class Script:
    """
    Bitcoin Script - Ngôn ngữ lập trình đơn giản của Bitcoin.
    
    Script được sử dụng trong:
    - scriptPubKey (locking script): Định nghĩa điều kiện để chi tiêu output
    - scriptSig (unlocking script): Cung cấp dữ liệu để thỏa mãn điều kiện
    
    Ví dụ P2PKH (Pay-to-Public-Key-Hash):
        scriptPubKey: ['OP_DUP', 'OP_HASH160', <pubkey_hash>, 'OP_EQUALVERIFY', 'OP_CHECKSIG']
        scriptSig: [<signature>, <public_key>]
    
    Attributes:
        cmds: Danh sách các lệnh/dữ liệu trong script
    """
    __slots__ = ['cmds']
    
    def __init__(self, cmds: Optional[List[Any]] = None):
        """
        Khởi tạo Script.
        
        Args:
            cmds: Danh sách lệnh, mặc định là rỗng
        """
        self.cmds: List[Any] = cmds if cmds is not None else []
    
    def __repr__(self) -> str:
        return f"Script({self.cmds})"
        
    def __str__(self) -> str:
        return str(self.cmds)
    
    def __add__(self, other: 'Script') -> 'Script':
        """Nối hai Script lại với nhau."""
        return Script(self.cmds + other.cmds)
    
    def __len__(self) -> int:
        """Số lượng lệnh trong script."""
        return len(self.cmds)
    
    def __bool__(self) -> bool:
        """Script rỗng = False, có lệnh = True."""
        return len(self.cmds) > 0
    
    def serialize(self) -> bytes:
        """
        Serialize script thành bytes.
        """
        result = bytearray()
        for cmd in self.cmds:
            if isinstance(cmd, int):
                result.append(cmd)
            elif isinstance(cmd, bytes):
                result.extend(encode_varint(len(cmd)))
                result.extend(cmd)
            elif isinstance(cmd, str):
                # Giả định string là hex hoặc opcode
                if cmd.startswith('OP_'):
                    # Đây là opcode (giản lược cho demo)
                    result.append(0x61) # Placeholder cho opcode
                else:
                    try:
                        b = bytes.fromhex(cmd)
                        result.extend(encode_varint(len(b)))
                        result.extend(b)
                    except ValueError:
                        b = cmd.encode('utf-8')
                        result.extend(encode_varint(len(b)))
                        result.extend(b)
        return bytes(result)


# =============================================================================
# TXIN CLASS - Transaction Input
# =============================================================================

class TxIn:
    """
    Transaction Input - Tham chiếu đến UTXO (Unspent Transaction Output).
    
    Mỗi input "chi tiêu" một output từ transaction trước bằng cách:
    1. Tham chiếu đến transaction chứa output đó (prev_tx)
    2. Chỉ định index của output trong transaction đó (prev_index)
    3. Cung cấp script để unlock output (script_sig)
    
    Attributes:
        prev_tx: Hash của transaction chứa UTXO được chi tiêu
        prev_index: Index của output trong transaction đó
        script_sig: Unlocking script (signature + public key)
        sequence: Sequence number cho RBF và timelocks
    """
    __slots__ = ['prev_tx', 'prev_index', 'script_sig', 'sequence']
    
    def __init__(
        self, 
        prev_tx: str, 
        prev_index: int, 
        script_sig: Optional[Script] = None, 
        sequence: int = DEFAULT_SEQUENCE
    ):
        """
        Khởi tạo Transaction Input.
        
        Args:
            prev_tx: Hash của transaction trước (64 hex chars)
            prev_index: Index của output được chi tiêu (0-based)
            script_sig: Unlocking script, mặc định rỗng
            sequence: Sequence number, mặc định 0xffffffff
        """
        self.prev_tx = prev_tx
        self.prev_index = prev_index
        self.script_sig = script_sig if script_sig is not None else Script()
        self.sequence = sequence
    
    def is_coinbase(self) -> bool:
        """
        Kiểm tra xem input này có phải là coinbase hay không.
        
        Coinbase input có đặc điểm:
        - prev_tx là 32 bytes zeros
        - prev_index là 0xffffffff
        """
        return (
            self.prev_tx == COINBASE_PREV_TX and 
            self.prev_index == COINBASE_PREV_INDEX
        )
        
    def to_dict(self) -> dict:
        """Chuyển đổi thành dictionary để serialize."""
        cmds = []
        for cmd in self.script_sig.cmds:
            if isinstance(cmd, bytes):
                cmds.append(cmd.hex())
            else:
                cmds.append(cmd)
                
        return {
            'prev_tx': self.prev_tx,
            'prev_index': self.prev_index,
            'script_sig': cmds,
            'sequence': self.sequence
        }


# =============================================================================
# TXOUT CLASS - Transaction Output
# =============================================================================

class TxOut:
    """
    Transaction Output - Định nghĩa số tiền và điều kiện chi tiêu.
    
    Output chứa:
    - Số lượng satoshis (1 BTC = 100,000,000 satoshis)
    - Script định nghĩa ai có thể chi tiêu (thường là P2PKH)
    
    Output chưa được chi tiêu gọi là UTXO (Unspent Transaction Output).
    
    Attributes:
        amount: Số satoshis (phải >= 0)
        script_pubkey: Locking script định nghĩa điều kiện chi tiêu
    """
    __slots__ = ['amount', 'script_pubkey']
    
    def __init__(self, amount: int, script_pubkey: Script):
        """
        Khởi tạo Transaction Output.
        
        Args:
            amount: Số satoshis (1 BTC = 10^8 satoshis)
            script_pubkey: Locking script
            
        Raises:
            ValueError: Nếu amount < 0
        """
        if amount < 0:
            raise ValueError(f"Amount cannot be negative: {amount}")
        self.amount = amount
        self.script_pubkey = script_pubkey
        
    def to_dict(self) -> dict:
        """Chuyển đổi thành dictionary để serialize."""
        cmds = []
        for cmd in self.script_pubkey.cmds:
            if isinstance(cmd, bytes):
                cmds.append(cmd.hex())
            else:
                cmds.append(cmd)

        return {
            'amount': self.amount,
            'script_pubkey': cmds
        }


# =============================================================================
# TX CLASS - Complete Transaction
# =============================================================================

class Tx:
    """
    Bitcoin Transaction - Chứa đầy đủ thông tin của một giao dịch.
    
    Cấu trúc transaction:
    ┌─────────────────────────────────────────────┐
    │ Version (4 bytes)                           │
    ├─────────────────────────────────────────────┤
    │ Input Count (VarInt)                        │
    │ ┌─────────────────────────────────────────┐ │
    │ │ Input 1: prev_tx + prev_index +         │ │
    │ │          script_sig + sequence          │ │
    │ ├─────────────────────────────────────────┤ │
    │ │ Input 2: ...                            │ │
    │ └─────────────────────────────────────────┘ │
    ├─────────────────────────────────────────────┤
    │ Output Count (VarInt)                       │
    │ ┌─────────────────────────────────────────┐ │
    │ │ Output 1: amount + script_pubkey        │ │
    │ ├─────────────────────────────────────────┤ │
    │ │ Output 2: ...                           │ │
    │ └─────────────────────────────────────────┘ │
    ├─────────────────────────────────────────────┤
    │ Locktime (4 bytes)                          │
    └─────────────────────────────────────────────┘
    
    Attributes:
        version: Phiên bản transaction (thường là 1 hoặc 2)
        tx_ins: Danh sách inputs
        tx_outs: Danh sách outputs
        locktime: Thời điểm sớm nhất transaction có thể được confirm
    """
    __slots__ = ['version', 'tx_ins', 'tx_outs', 'locktime']
    
    def __init__(
        self, 
        version: int, 
        tx_ins: List[TxIn], 
        tx_outs: List[TxOut], 
        locktime: int
    ):
        """
        Khởi tạo Transaction.
        
        Args:
            version: Phiên bản (1 = legacy, 2 = với CSV support)
            tx_ins: Danh sách Transaction Inputs
            tx_outs: Danh sách Transaction Outputs
            locktime: Block height hoặc timestamp (0 = không giới hạn)
        """
        self.version = version
        self.tx_ins = tx_ins
        self.tx_outs = tx_outs
        self.locktime = locktime

    def id(self) -> str:
        """
        Tính Transaction ID (TXID).
        
        TXID = reverse(double_sha256(serialized_tx))
        
        Bitcoin hiển thị TXID theo thứ tự byte đảo ngược (little-endian).
        
        Returns:
            str: TXID dưới dạng hex string (64 ký tự)
        """
        tx_serialized = self.serialize()
        # Double SHA-256
        tx_hash = hashlib.sha256(hashlib.sha256(tx_serialized).digest()).digest()
        # Đảo ngược bytes để ra TXID format chuẩn
        return tx_hash[::-1].hex()
    
    def serialize(self) -> bytes:
        """
        Serialize transaction thành bytes theo format Bitcoin.
        
        Format:
        - Version: 4 bytes, little-endian
        - Input count: VarInt
        - Inputs: mỗi input gồm prev_tx + prev_index + script_sig + sequence
        - Output count: VarInt  
        - Outputs: mỗi output gồm amount + script_pubkey
        - Locktime: 4 bytes, little-endian
        
        Returns:
            bytes: Transaction đã serialize
        """
        result = bytearray()
        
        # 1. Version (4 bytes, little-endian)
        result.extend(self.version.to_bytes(4, 'little'))
        
        # 2. Input count (VarInt)
        result.extend(encode_varint(len(self.tx_ins)))
        
        # 3. Serialize từng input
        for tx_in in self.tx_ins:
            # Previous tx hash (32 bytes, reversed to little-endian)
            prev_tx_bytes = bytes.fromhex(tx_in.prev_tx)[::-1]
            result.extend(prev_tx_bytes)
            
            # Previous output index (4 bytes, little-endian)
            result.extend(tx_in.prev_index.to_bytes(4, 'little'))
            
            # ScriptSig (VarInt length + script bytes)
            script_sig = tx_in.script_sig.serialize()
            result.extend(encode_varint(len(script_sig)))
            result.extend(script_sig)
            
            # Sequence (4 bytes, little-endian)
            result.extend(tx_in.sequence.to_bytes(4, 'little'))
        
        # 4. Output count (VarInt)
        result.extend(encode_varint(len(self.tx_outs)))
        
        # 5. Serialize từng output
        for tx_out in self.tx_outs:
            # Amount (8 bytes, little-endian)
            result.extend(tx_out.amount.to_bytes(8, 'little'))
            
            # ScriptPubKey (VarInt length + script bytes)
            script_pubkey = tx_out.script_pubkey.serialize()
            result.extend(encode_varint(len(script_pubkey)))
            result.extend(script_pubkey)
        
        # 6. Locktime (4 bytes, little-endian)
        result.extend(self.locktime.to_bytes(4, 'little'))
        
        return bytes(result)

    def sig_hash(self, input_index: int, script_pubkey: Script) -> bytes:
        """
        Tính hash của transaction để ký/xác thực (SIGHASH_ALL).
        
        Quy trình chuẩn Bitcoin (Legacy):
        1. Tạo bản sao của transaction
        2. Xóa script_sig của tất cả inputs
        3. Gán script_pubkey (của UTXO đang chi) vào script_sig của input tương ứng
        4. Serialize transaction + append SIGHASH_TYPE (1 = SIGHASH_ALL)
        5. Double SHA-256
        
        Args:
            input_index: Index của input đang được xử lý
            script_pubkey: Locking script của UTXO mà input này đang chi tiêu
            
        Returns:
            bytes: 32-byte hash
        """
        # 1. Tạo bản sao (deep copy đơn giản)
        temp_ins = []
        for i, tx_in in enumerate(self.tx_ins):
            if i == input_index:
                # Gán script_pubkey cho input đang xét
                temp_ins.append(TxIn(tx_in.prev_tx, tx_in.prev_index, script_pubkey, tx_in.sequence))
            else:
                # Xóa script_sig cho các inputs khác
                temp_ins.append(TxIn(tx_in.prev_tx, tx_in.prev_index, Script(), tx_in.sequence))
        
        temp_tx = Tx(self.version, temp_ins, self.tx_outs, self.locktime)
        
        # 2. Serialize + SIGHASH_ALL (1)
        # SIGHASH_ALL là 4 bytes little-endian
        s = temp_tx.serialize() + (1).to_bytes(4, 'little')
        
        # 3. Double SHA-256
        return hashlib.sha256(hashlib.sha256(s).digest()).digest()

    def is_coinbase(self) -> bool:
        """
        Kiểm tra xem đây có phải là Coinbase transaction không.
        
        Coinbase transaction:
        - Là transaction đầu tiên trong mỗi block
        - Tạo ra Bitcoin mới (block reward + fees)
        - Có đúng 1 input với prev_tx = zeros và prev_index = 0xffffffff
        
        Returns:
            bool: True nếu là coinbase transaction
        """
        if len(self.tx_ins) != 1:
            return False
        return self.tx_ins[0].is_coinbase()
        
    def to_dict(self) -> dict:
        """
        Chuyển đổi transaction thành dictionary.
        
        Hữu ích cho việc serialize sang JSON hoặc lưu vào database.
        """
        return {
            'txid': self.id(),
            'version': self.version,
            'tx_ins': [tx_in.to_dict() for tx_in in self.tx_ins],
            'tx_outs': [tx_out.to_dict() for tx_out in self.tx_outs],
            'locktime': self.locktime,
            'is_coinbase': self.is_coinbase()
        }

    def total_output_amount(self) -> int:
        """Tính tổng số satoshis của tất cả outputs."""
        return sum(tx_out.amount for tx_out in self.tx_outs)

    @classmethod
    def create_coinbase(
        cls, 
        amount: int, 
        script_pubkey: Script, 
        height: int = 0
    ) -> 'Tx':
        """
        Tạo Coinbase transaction (transaction đầu tiên trong block).
        
        Coinbase transaction:
        - Không có input thực (prev_tx = zeros)
        - Tạo ra Bitcoin mới từ block reward
        - ScriptSig chứa block height (BIP34) và dữ liệu tùy ý
        
        Args:
            amount: Block reward (satoshis), giảm 50% mỗi 210,000 blocks
            script_pubkey: Locking script cho output (thường là P2PKH của miner)
            height: Block height (dùng trong scriptSig theo BIP34)
            
        Returns:
            Tx: Coinbase transaction
            
        Example:
            >>> script = Script(['OP_DUP', 'OP_HASH160', pubkey_hash, 'OP_EQUALVERIFY', 'OP_CHECKSIG'])
            >>> coinbase = Tx.create_coinbase(amount=50*10**8, script_pubkey=script, height=1)
        """
        # ScriptSig chứa block height và message tùy ý
        coinbase_message = f"Block {height} reward".encode('utf-8')
        script_sig = Script([
            height.to_bytes(4, 'little'),  # Block height (BIP34 requirement)
            len(coinbase_message).to_bytes(1, 'little'),
            coinbase_message
        ])
        
        # Coinbase input đặc biệt
        tx_in = TxIn(
            prev_tx=COINBASE_PREV_TX,
            prev_index=COINBASE_PREV_INDEX,
            script_sig=script_sig,
            sequence=DEFAULT_SEQUENCE
        )
        
        # Output gửi reward cho miner
        tx_out = TxOut(amount=amount, script_pubkey=script_pubkey)
        
        return cls(version=1, tx_ins=[tx_in], tx_outs=[tx_out], locktime=0)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("BITCOIN TRANSACTION DEMO")
    print("=" * 60)
    
    try:
        # Tạo P2PKH script cho miner
        pubkey_hash = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
        script_pubkey = Script([
            "OP_DUP", 
            "OP_HASH160", 
            pubkey_hash, 
            "OP_EQUALVERIFY", 
            "OP_CHECKSIG"
        ])
        
        # Tạo coinbase transaction (50 BTC block reward)
        block_height = 123456
        reward_btc = 50
        reward_satoshis = reward_btc * 100_000_000
        
        coinbase_tx = Tx.create_coinbase(
            amount=reward_satoshis,
            script_pubkey=script_pubkey,
            height=block_height
        )
        
        # Hiển thị thông tin
        print(f"\n📦 Coinbase Transaction for Block #{block_height}")
        print(f"   TXID: {coinbase_tx.id()}")
        print(f"   Is Coinbase: {coinbase_tx.is_coinbase()}")
        print(f"   Inputs: {len(coinbase_tx.tx_ins)}")
        print(f"   Outputs: {len(coinbase_tx.tx_outs)}")
        print(f"   Reward: {reward_btc} BTC ({reward_satoshis:,} satoshis)")
        
        # Hiển thị chi tiết output
        print(f"\n📤 Output Details:")
        for i, tx_out in enumerate(coinbase_tx.tx_outs):
            print(f"   Output #{i}: {tx_out.amount:,} satoshis")
            print(f"   Script: {tx_out.script_pubkey}")
        
    except Exception as e:
        print(f"❌ Error: {e}")