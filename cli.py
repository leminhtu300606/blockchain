"""
Bitcoin Blockchain CLI - Giao diện dòng lệnh cho người dùng

Cung cấp menu tương tác để:
- Tạo ví mới
- Xem thông tin ví
- Gửi BTC
- Xem blockchain
- Đào block mới

Chạy: python cli.py
"""
import sys
import os
import time

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from client.account import Account, generate_account
from client.sendBTC import UTXO, TxOutput, create_transaction
from core.blockchain import Blockchain
from core.database.database import BlockchainDB, UTXOSet
from core.mempool import mempool
from core.Tx import Tx, TxIn, TxOut, Script


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def clear_screen():
    """Xóa màn hình console."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str):
    """In tiêu đề đẹp."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_menu():
    """In menu chính."""
    print_header("BITCOIN BLOCKCHAIN - MENU CHÍNH")
    print("""
    [1] 🆕 Tạo ví mới
    [2] 📥 Import ví từ Private Key
    [3] 💰 Xem số dư ví
    [4] 💸 Gửi BTC
    [5] ⛏️  Đào block mới
    [6] 📊 Xem thông tin Blockchain
    [7] 🔍 Xem block theo Height
    [8] 📜 Xem lịch sử giao dịch
    [0] ❌ Thoát
    """)


def pause():
    """Dừng màn hình chờ người dùng."""
    input("\n⏎ Nhấn Enter để tiếp tục...")


# =============================================================================
# FEATURE FUNCTIONS
# =============================================================================

def create_new_wallet():
    """Tạo ví Bitcoin mới."""
    print_header("TẠO VÍ MỚI")
    
    keys = generate_account()
    
    print("\n✅ Ví đã được tạo thành công!")
    print("\n" + "-" * 50)
    print(f"🔐 Private Key (BÍ MẬT - KHÔNG CHIA SẺ!):")
    print(f"   {keys['private_key']}")
    print(f"\n🔑 Public Key:")
    print(f"   {keys['public_key']}")
    print(f"\n📬 Địa chỉ Bitcoin:")
    print(f"   {keys['address']}")
    print("-" * 50)
    print("\n⚠️  LƯU Ý: Hãy lưu Private Key ở nơi an toàn!")
    
    pause()


def import_wallet():
    """Import ví từ Private Key."""
    print_header("IMPORT VÍ")
    
    private_key = input("\n🔐 Nhập Private Key (hex): ").strip()
    
    if len(private_key) != 64:
        print("❌ Private Key không hợp lệ! Phải có đúng 64 ký tự hex.")
        pause()
        return
    
    try:
        account = Account(private_key=private_key)
        keys = account.create_keys()
        
        print("\n✅ Import thành công!")
        print(f"📬 Địa chỉ: {keys['address']}")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    
    pause()


def check_balance():
    """Xem số dư của một địa chỉ."""
    print_header("XEM SỐ DƯ")
    
    address = input("\n📬 Nhập địa chỉ ví (hoặc pubkey hash): ").strip()
    
    if not address:
        print("❌ Địa chỉ không được để trống!")
        pause()
        return
    
    utxo_set = UTXOSet()
    balance = utxo_set.get_balance(address)
    
    btc = balance / (10 ** 8)
    print(f"\n💰 Số dư: {balance:,} satoshi ({btc:.8f} BTC)")
    
    print("\n⚠️  Lịch sử giao dịch chi tiết tạm thời bị vô hiệu hóa trong bản nâng cấp UTXO.")
    
    pause()


def send_btc():
    """Gửi BTC cho người khác."""
    print_header("GỬI BTC")
    
    print("\n📝 Nhập thông tin giao dịch:")
    
    # Thông tin nguồn tiền
    print("\n--- NGUỒN TIỀN (UTXO) ---")
    prev_txid = input("   TXID của giao dịch cũ: ").strip()
    if not prev_txid:
        prev_txid = "0" * 64  # Demo
    
    try:
        prev_index = int(input("   Output index (mặc định 0): ").strip() or "0")
        input_amount = int(input("   Số satoshi trong UTXO: ").strip() or "0")
    except ValueError:
        print("❌ Số không hợp lệ!")
        pause()
        return
    
    # Thông tin người gửi
    print("\n--- NGƯỜI GỬI ---")
    sender_privkey = input("   Private Key của bạn: ").strip()
    sender_address = input("   Địa chỉ của bạn (pubkey hash): ").strip()
    
    # Thông tin người nhận
    print("\n--- NGƯỜI NHẬN ---")
    recipient_address = input("   Địa chỉ người nhận: ").strip()
    
    try:
        send_amount = int(input("   Số satoshi muốn gửi: ").strip() or "0")
    except ValueError:
        print("❌ Số không hợp lệ!")
        pause()
        return
    
    if send_amount <= 0:
        print("❌ Số tiền phải lớn hơn 0!")
        pause()
        return
    
    if send_amount > input_amount:
        print("❌ Không đủ tiền!")
        pause()
        return
    
    # Tạo giao dịch đơn giản và thêm vào mempool
    print("\n⏳ Đang tạo giao dịch...")
    
    try:
        # Tạo output
        tx_out = TxOut(
            amount=send_amount, 
            script_pubkey=Script([
                'OP_DUP', 'OP_HASH160', 
                recipient_address, 
                'OP_EQUALVERIFY', 'OP_CHECKSIG'
            ])
        )
        
        # Tạo input
        tx_in = TxIn(
            prev_tx=prev_txid,
            prev_index=prev_index,
            script_sig=Script([sender_address]),  # Simplified
            sequence=0xffffffff
        )
        
        # Tạo transaction
        tx = Tx(version=1, tx_ins=[tx_in], tx_outs=[tx_out], locktime=0)
        txid = tx.id()
        
        # Thêm vào mempool
        fee = input_amount - send_amount
        mempool.transactions[txid] = {
            'tx': tx, 
            'timestamp': time.time(), 
            'fee': fee, 
            'size': 200
        }
        mempool._fee_heap.append((-fee/200, txid))
        
        print(f"\n✅ Giao dịch đã được tạo!")
        print(f"   TXID: {txid[:32]}...")
        print(f"   Số tiền: {send_amount:,} satoshi")
        print(f"   Phí: {fee:,} satoshi")
        print(f"\n📝 Giao dịch đang chờ trong Mempool.")
        print(f"   Chạy 'Đào block mới' để xác nhận giao dịch.")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    
    pause()


def mine_block():
    """Đào một block mới."""
    print_header("ĐÀO BLOCK MỚI")
    
    print("\n⛏️  Đang khởi tạo...")
    
    try:
        bc = Blockchain()
        last_block = bc.fetch_last_block()
        
        if last_block is None:
            print("❌ Không tìm thấy blockchain!")
            pause()
            return
        
        new_height = last_block['Height'] + 1
        prev_hash = last_block['Blockheader']['blockhash']
        
        print(f"\n📊 Block hiện tại: #{last_block['Height']}")
        print(f"⏳ Đang đào block #{new_height}...")
        
        start_time = time.time()
        bc.add_block(new_height, prev_hash)
        elapsed = time.time() - start_time
        
        print(f"\n✅ Block #{new_height} đã được đào thành công!")
        print(f"   Thời gian: {elapsed:.2f} giây")
        print(f"   Phần thưởng: 50 BTC")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    
    pause()


def view_blockchain_info():
    """Xem thông tin tổng quan blockchain."""
    print_header("THÔNG TIN BLOCKCHAIN")
    
    db = BlockchainDB()
    blocks = db.read()
    
    if not blocks:
        print("\n❌ Blockchain trống!")
        pause()
        return
    
    last_block = blocks[-1]
    
    print(f"\n📊 Tổng số blocks: {len(blocks)}")
    print(f"📏 Block mới nhất: #{last_block.get('Height', len(blocks)-1)}")
    
    if 'Blockheader' in last_block:
        header = last_block['Blockheader']
        print(f"🔗 Hash: {header.get('blockhash', 'N/A')[:32]}...")
        print(f"⏰ Timestamp: {header.get('timestamp', 'N/A')}")
        print(f"🎯 Bits: {header.get('bits', 'N/A')}")
        print(f"🔢 Nonce: {header.get('nonce', 'N/A')}")
    
    # Thống kê mempool
    print(f"\n📦 Mempool: {mempool.get_size()} giao dịch đang chờ")
    
    pause()


def view_block_by_height():
    """Xem chi tiết một block theo height."""
    print_header("XEM BLOCK THEO HEIGHT")
    
    try:
        height = int(input("\n📏 Nhập block height: ").strip())
    except ValueError:
        print("❌ Height phải là số!")
        pause()
        return
    
    db = BlockchainDB()
    blocks = db.read()
    
    if height < 0 or height >= len(blocks):
        print(f"❌ Block #{height} không tồn tại!")
        pause()
        return
    
    block = blocks[height]
    
    print(f"\n📦 BLOCK #{height}")
    print("-" * 50)
    
    if 'Blockheader' in block:
        header = block['Blockheader']
        print(f"🔗 Hash: {header.get('blockhash', 'N/A')}")
        print(f"⬅️  Prev: {header.get('previous_block_hash', 'N/A')[:32]}...")
        print(f"🌳 Merkle: {header.get('merkle_root', 'N/A')[:32]}...")
        print(f"⏰ Time: {header.get('timestamp', 'N/A')}")
        print(f"🔢 Nonce: {header.get('nonce', 'N/A')}")
    
    txs = block.get('Txs', [])
    print(f"\n📜 Giao dịch: {len(txs)}")
    
    for i, tx in enumerate(txs[:3]):  # Hiển thị tối đa 3 tx
        print(f"\n   TX #{i}: {tx.get('txid', 'N/A')[:32]}...")
        if tx.get('is_coinbase'):
            print(f"   📍 Loại: Coinbase (Thưởng block)")
        
        for out in tx.get('tx_outs', []):
            print(f"   💰 Output: {out.get('amount', 0):,} satoshi")
    
    if len(txs) > 3:
        print(f"\n   ... và {len(txs) - 3} giao dịch khác")
    
    pause()


def view_transaction_history():
    """Xem lịch sử giao dịch của một địa chỉ."""
    print_header("LỊCH SỬ GIAO DỊCH")
    
    address = input("\n📬 Nhập địa chỉ (pubkey hash): ").strip()
    
    if not address:
        print("❌ Địa chỉ không được để trống!")
        pause()
        return
    
    print(f"\n⚠️  Tính năng xem lịch sử giao dịch đang được bảo trì để nâng cấp lên UTXO model.")
    print("Vui lòng kiểm tra số dư hiện tại để xác nhận giao dịch.")
    
    pause()


# =============================================================================
# MAIN LOOP
# =============================================================================

def main():
    """Vòng lặp chính của CLI."""
    while True:
        clear_screen()
        print_menu()
        
        choice = input("👉 Chọn chức năng (0-8): ").strip()
        
        if choice == "1":
            create_new_wallet()
        elif choice == "2":
            import_wallet()
        elif choice == "3":
            check_balance()
        elif choice == "4":
            send_btc()
        elif choice == "5":
            mine_block()
        elif choice == "6":
            view_blockchain_info()
        elif choice == "7":
            view_block_by_height()
        elif choice == "8":
            view_transaction_history()
        elif choice == "0":
            print("\n👋 Tạm biệt!")
            break
        else:
            print("\n❌ Lựa chọn không hợp lệ!")
            pause()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Đã thoát.")
