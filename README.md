# Hướng dẫn Sử dụng Chi tiết & Mô tả Chức năng Hệ thống Blockchain

Tài liệu này cung cấp cái nhìn chi tiết về cách sử dụng hệ thống và vai trò của từng file trong dự án.

---

## 1. Hướng dẫn Sử dụng

### Cài đặt Môi trường
1. **Python:** Yêu cầu Python 3.8 trở lên.
2. **Cài đặt thư viện:**
   ```bash
   pip install -r requirements.txt
   ```

### Khởi chạy Node
Để chạy một node blockchain (bao gồm Mining, API, và P2P):
```bash
python backend/main.py
```
*Mặc định Node sẽ chạy tại cổng API 5000 và cổng P2P 6000.*

### Chạy hệ thống nhiều Node (Mô phỏng mạng lưới)
Bạn có thể mở nhiều terminal để chạy nhiều node khác nhau:
- **Node 1:** `PORT=5000 P2P_PORT=6000 python backend/main.py`
- **Node 2:** `PORT=5001 P2P_PORT=6001 SEED_NODE=localhost:6000 python backend/main.py`

### Các thao tác cơ bản
- **Mining:** Hệ thống tự động mine block mới khi có giao dịch hoặc định kỳ.
- **Gửi giao dịch:** Sử dụng API POST `/api/transaction/verify` hoặc dùng client script (nếu có).
- **Kiểm tra lịch sử:** Truy cập API GET `/api/history/blocks`.

---

## 2. Danh sách File và Chức năng

### Thư mục `backend/core/` (Lõi hệ thống)
- **[blockchain.py](file:///h:/Blockchain/backend/core/blockchain.py):** "Bộ não" của hệ thống. Quản lý chuỗi khối, xử lý logic thêm block mới, điều chỉnh độ khó (Difficulty Adjustment) và vòng lặp mining.
- **[Tx.py](file:///h:/Blockchain/backend/core/Tx.py):** Định nghĩa cấu trúc dữ liệu Transaction, TxIn, TxOut và Script. Xử lý việc serialize dữ liệu và tính toán mã băm để ký (sig_hash).
- **[transaction_verifier.py](file:///h:/Blockchain/backend/core/transaction_verifier.py):** Chuyên trách việc xác thực giao dịch. Kiểm tra chữ ký ECDSA, số dư UTXO và logic kịch bản P2PKH.
- **[block.py](file:///h:/Blockchain/backend/core/block.py):** Định nghĩa cấu trúc của một Block (bao gồm Header và danh sách Transactions).
- **[blockheader.py](file:///h:/Blockchain/backend/core/blockheader.py):** Chứa thông tin Metadata của block. Xử lý thuật toán Proof-of-Work (mining) và tính toán mục tiêu độ khó (Target).
- **[mempool.py](file:///h:/Blockchain/backend/core/mempool.py):** Quản lý các giao dịch chưa được xác nhận (Unconfirmed Transactions). Sắp xếp giao dịch theo phí (fee) để ưu tiên đưa vào block.
- **[p2p_node.py](file:///h:/Blockchain/backend/core/p2p_node.py):** Xử lý giao thức mạng ngang hàng. Cho phép các node tìm thấy nhau và lan truyền dữ liệu (Gossip protocol).
- **[database/database.py](file:///h:/Blockchain/backend/core/database/database.py):** Quản lý việc lưu trữ dữ liệu bền vững vào file JSON (`blockchain.json`) và theo dõi số dư ví.

### Thư mục `backend/util/` (Công cụ hỗ trợ)
- **[merkle.py](file:///h:/Blockchain/backend/util/merkle.py):** Tính toán Merkle Root để đảm bảo tính toàn vẹn của danh sách giao dịch trong block.
- **[util.py](file:///h:/Blockchain/backend/util/util.py):** Các hàm băm hỗ trợ như `hash256` (double SHA-256) và `hash160`.
- **[block_utils.py](file:///h:/Blockchain/backend/util/block_utils.py):** Các hàm tiện ích để khởi tạo Block Genesis và xây dựng block từ mempool.
- **[tx_utils.py](file:///h:/Blockchain/backend/util/tx_utils.py):** Công cụ hỗ trợ tạo cặp khóa (keypair) và ký thử nghiệm giao dịch cho mục đích testing.

### Thư mục `backend/api/` (Giao diện lập trình)
- **[transaction_api.py](file:///h:/Blockchain/backend/api/transaction_api.py):** Định nghĩa các đầu cuối HTTP để gửi và xác thực giao dịch từ bên ngoài.
- **[history_api.py](file:///h:/Blockchain/backend/api/history_api.py):** Cung cấp dữ liệu về lịch sử chuỗi khối và số dư cho Frontend.

### File tại thư mục gốc
- **[main.py](file:///h:/Blockchain/backend/main.py):** Điểm khởi đầu của ứng dụng. Thiết lập cấu hình Flask, P2P và kết nối các thành phần lại với nhau.
- **[verify_balance.py](file:///h:/Blockchain/verify_balance.py):** Script kiểm tra nhanh sự thay đổi số dư và tính đúng đắn của sổ cái.
- **[requirements.txt](file:///h:/Blockchain/requirements.txt):** Danh sách các thư viện cần thiết để cài đặt.

---
*Tài liệu này được soạn thảo để hỗ trợ việc quản lý và phát triển dự án Blockchain của bạn.*
