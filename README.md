# 🌌 BLOCKCHAIN: Premium Blockchain Ecosystem (Python)

Blockchain là một hệ sinh thái Blockchain hoàn chỉnh, mô phỏng các nguyên lý cốt lõi của Bitcoin với giao diện người dùng hiện đại, bảo mật chữ ký số ECDSA, cơ chế đồng thuận PoW động, và mạng lưới P2P phân tán.

![Giao diện Blockchain](file:///C:/Users/Tu/.gemini/antigravity/brain/35bfff51-d19a-434c-a895-c4013ce5e379/premium_blockchain_ui_mockup_1766756696463.png)

---

## 🛠️ 1. Hướng dẫn Khởi chạy (Quick Start)

### Cài đặt Môi trường
1. **Yêu cầu:** Python 3.8+
2. **Cài đặt thư viện:**
   ```bash
   pip install -r requirements.txt
   ```

### Chạy Backend (API & P2P)
Backend xử lý logic blockchain, khai thác (mining) và giao tiếp mạng.
```powershell
# Chạy node đơn lẻ (Cổng API: 5000, P2P: 6000)
python backend/main.py
```

### Chạy Frontend (Aetherium UI)
Giao diện người dùng cao cấp để quản lý ví và theo dõi chuỗi.
```powershell
# Chạy Server giao diện (Mặc định: http://localhost:5001)
python frontend/app.py
```

---

## 🌐 2. Chạy Mạng lưới Đa Node (Multi-node Network)

Để giả lập mạng lưới phi tập trung, bạn có thể chạy nhiều node trên cùng một máy bằng cách thay đổi cổng:

**Terminal 1 (Seed Node):**
```powershell
set PORT=5000 && set P2P_PORT=6000 && python backend/main.py
```

**Terminal 2 (Peer Node):**
```powershell
set PORT=5002 && set P2P_PORT=6001 && set SEED_NODE=localhost:6000 && python backend/main.py
```

---

## 📂 3. Cấu trúc Hệ thống

### 🧠 Backend Core (`backend/core/`)
- **`blockchain.py`**: Lõi quản lý chuỗi, điều chỉnh độ khó và chọn chuỗi dài nhất.
- **`Tx.py`**: Cấu trúc giao dịch UTXO và logic băm dữ liệu.
- **`transaction_verifier.py`**: Xác thực chữ ký **ECDSA** (secp256k1) cực kỳ bảo mật.
- **`p2p_node.py`**: Giao thức mạng ngang hàng (Socket-based).
- **`database/`**: Lưu trữ dữ liệu JSON (`blockchain.json`) và sổ cái số dư.

### 🎨 Frontend UI (`frontend/`)
- **`app.py`**: Flask server phục vụ giao diện Blockchain.
- **`templates/`**: Chứa các file HTML (Glassmorphism theme).
  - `index.html`: Dashboard tổng quan và quản lý thợ đào.
  - `wallet.html`: Ví điện tử (Tạo khóa, kiểm tra số dư).
  - `verify_transaction.html`: Trung tâm an ninh xác thực giao dịch.
  - `blocks.html` & `history.html`: Trình khám phá chuỗi khối.

---

## 🌟 4. Các Tính năng Đột phá

- 💎 **Giao diện Glassmorphism**: Thiết kế hiện đại, sang trọng, mang lại trải nghiệm Web3 chuyên nghiệp.
- 🔐 **Bảo mật Tuyệt đối**: Tích hợp chữ ký số ECDSA thực, ngăn chặn gian lận giao dịch.
- ⚙️ **Mining Động**: Hệ thống tự động điều chỉnh độ khó để duy trì tốc độ sinh block ổn định.
- 💰 **Quản lý Ví Thông minh**: Tự động theo dõi số dư (UTXO set) và lịch sử biến động tài sản.
- 📡 **P2P Ready**: Kiến trúc mạng sẵn sàng cho việc kết nối và phân tán dữ liệu toàn cầu.

---

## 🎮 5. Hướng dẫn Trải nghiệm (User Workflows)

Để hiểu cách Blockchain hoạt động, bạn hãy thử thực hiện quy trình sau:

### Bước 1: Thiết lập Danh tính (Wallet)
1. Truy cập [http://localhost:5001/wallet](http://localhost:5001/wallet).
2. Nhấn **"Generate New Identity"**. 
3. Hệ thống sẽ tạo ra một cặp khóa ECDSA. Hãy copy **Public Address** (Địa chỉ ví) của bạn.
   - *Giải thích:* Đây là cách bạn tạo ra "tài khoản" mà không cần bất kỳ ngân hàng nào cấp phép.

### Bước 2: Bắt đầu Khai thác (Mining)
1. Quay lại trang **Dashboard**.
2. Nhấn nút **"Start Miner"**.
3. Quan sát mục **Hashrate** và terminal chạy backend. Khi thợ đào tìm thấy block mới, số dư của bạn sẽ tăng lên (do được nhận thưởng coinbase).
   - *Giải thích:* Bạn đang đóng góp sức mạnh tính toán để bảo mật mạng lưới và được trả công bằng tiền mã hóa.

### Bước 3: Tra cứu & Kiểm tra (Explorer)
1. Sau khi đã đào được vài block, truy cập trang **Assets**.
2. Dán địa ví đã copy ở Bước 1 vào ô tìm kiếm.
3. Bạn sẽ thấy biểu đồ số dư tăng vọt và danh sách các block mà bạn đã nhận được thưởng.
4. Vào trang **Security** để thử nghiệm công cụ xác thực giao dịch bằng chữ ký số.

---
*Blockchain Protocol - Built for the future of decentralized technology.*
