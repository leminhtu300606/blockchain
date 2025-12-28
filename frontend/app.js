/**
 * Bitcoin Blockchain Frontend - JavaScript
 * Xử lý logic giao diện và gọi API
 */

// =============================================================================
// API CONFIG
// =============================================================================

const API_BASE = 'http://localhost:5000/api';

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Gọi API và trả về JSON
 */
async function callAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        });
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return { success: false, error: 'Không thể kết nối đến server' };
    }
}

/**
 * Hiển thị toast thông báo
 */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');

    toastMessage.textContent = message;
    toast.className = `toast ${type}`;

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

/**
 * Format timestamp thành ngày giờ
 */
function formatTime(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('vi-VN');
}

/**
 * Format số với dấu phẩy
 */
function formatNumber(num) {
    return num.toLocaleString('vi-VN');
}

// =============================================================================
// NAVIGATION
// =============================================================================

/**
 * Chuyển trang
 */
function navigateToPage(pageName) {
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === pageName) {
            item.classList.add('active');
        }
    });

    // Update pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(`page-${pageName}`).classList.add('active');

    // Load data for specific pages
    if (pageName === 'dashboard') {
        loadDashboard();
    }
}

// =============================================================================
// DASHBOARD
// =============================================================================

/**
 * Tải dữ liệu dashboard
 */
async function loadDashboard() {
    // Load blockchain info
    const infoResult = await callAPI('/blockchain/info');
    if (infoResult.success) {
        const data = infoResult.data;
        document.getElementById('total-blocks').textContent = formatNumber(data.totalBlocks);
        document.getElementById('latest-height').textContent = `#${data.latestHeight}`;
        document.getElementById('mempool-size').textContent = data.mempoolSize;
        document.getElementById('difficulty').textContent = data.difficulty || '-';
    }

    // Load recent blocks
    const blocksResult = await callAPI('/blockchain/blocks?limit=5');
    const tbody = document.getElementById('recent-blocks');

    if (blocksResult.success && blocksResult.data.length > 0) {
        tbody.innerHTML = blocksResult.data.map(block => `
            <tr>
                <td><strong>#${block.height}</strong></td>
                <td><code>${block.hash}</code></td>
                <td>${block.txCount}</td>
                <td>${formatTime(block.timestamp)}</td>
            </tr>
        `).join('');
    } else {
        tbody.innerHTML = '<tr><td colspan="4" class="loading">Không có dữ liệu</td></tr>';
    }
}

// =============================================================================
// WALLET
// =============================================================================

/**
 * Tạo ví mới
 */
async function createWallet() {
    const btn = document.getElementById('btn-create-wallet');
    btn.disabled = true;
    btn.textContent = 'Đang tạo...';

    const result = await callAPI('/wallet/create', { method: 'POST' });

    btn.disabled = false;
    btn.textContent = 'Tạo Ví';

    if (result.success) {
        const data = result.data;
        document.getElementById('new-private-key').textContent = data.privateKey;
        document.getElementById('new-public-key').textContent = data.publicKey;
        document.getElementById('new-address').textContent = data.address;
        document.getElementById('new-wallet-result').classList.remove('hidden');
        showToast('✅ Tạo ví thành công!', 'success');
    } else {
        showToast('❌ ' + result.error, 'error');
    }
}

/**
 * Kiểm tra số dư
 */
async function checkBalance() {
    const address = document.getElementById('balance-address').value.trim();

    if (!address) {
        showToast('❌ Vui lòng nhập địa chỉ', 'error');
        return;
    }

    const result = await callAPI(`/wallet/balance/${address}`);

    if (result.success) {
        const data = result.data;
        document.getElementById('balance-value').textContent = formatNumber(data.balance);
        document.getElementById('balance-btc').textContent = `≈ ${data.balanceBTC.toFixed(8)} BTC`;
        document.getElementById('balance-result').classList.remove('hidden');
    } else {
        showToast('❌ ' + result.error, 'error');
    }
}

// =============================================================================
// SEND TRANSACTION
// =============================================================================

/**
 * Gửi giao dịch
 */
async function sendTransaction(event) {
    event.preventDefault();

    const data = {
        recipient: document.getElementById('send-recipient').value.trim(),
        amount: document.getElementById('send-amount').value,
        prevTxid: document.getElementById('send-prev-txid').value.trim() || '0'.repeat(64),
        senderAddress: document.getElementById('send-sender').value.trim(),
        inputAmount: document.getElementById('send-amount').value
    };

    if (!data.recipient || !data.amount) {
        showToast('❌ Vui lòng nhập đầy đủ thông tin', 'error');
        return;
    }

    const result = await callAPI('/transaction/send', {
        method: 'POST',
        body: JSON.stringify(data)
    });

    if (result.success) {
        document.getElementById('send-txid').textContent = result.data.txid;
        document.getElementById('send-result').classList.remove('hidden');
        showToast('✅ Giao dịch đã được tạo!', 'success');

        // Reset form
        document.getElementById('send-form').reset();
    } else {
        showToast('❌ ' + result.error, 'error');
    }
}

// =============================================================================
// BLOCKS
// =============================================================================

/**
 * Tìm block theo height
 */
async function searchBlock() {
    const height = document.getElementById('search-height').value;

    if (height === '') {
        showToast('❌ Vui lòng nhập block height', 'error');
        return;
    }

    const result = await callAPI(`/blockchain/block/${height}`);

    if (result.success) {
        const data = result.data;
        document.getElementById('block-height').textContent = data.height;
        document.getElementById('block-hash').textContent = data.hash;
        document.getElementById('block-prev').textContent = data.previousHash.substring(0, 32) + '...';
        document.getElementById('block-merkle').textContent = data.merkleRoot.substring(0, 32) + '...';
        document.getElementById('block-time').textContent = formatTime(data.timestamp);
        document.getElementById('block-nonce').textContent = data.nonce;
        document.getElementById('block-txcount').textContent = data.txCount;
        document.getElementById('block-detail').classList.remove('hidden');
    } else {
        showToast('❌ ' + result.error, 'error');
        document.getElementById('block-detail').classList.add('hidden');
    }
}

// =============================================================================
// MINING
// =============================================================================

/**
 * Đào block mới
 */
async function mineBlock() {
    const btn = document.getElementById('btn-mine');
    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span> Đang đào...';

    const result = await callAPI('/blockchain/mine', { method: 'POST' });

    btn.disabled = false;
    btn.innerHTML = '<span>⛏️</span> Bắt Đầu Đào';

    if (result.success) {
        const data = result.data;
        document.getElementById('mine-height').textContent = `#${data.height}`;
        document.getElementById('mine-time').textContent = `${data.time}s`;
        document.getElementById('mine-reward').textContent = `${data.reward} BTC`;
        document.getElementById('mine-result').classList.remove('hidden');
        showToast('🎉 Đào block thành công!', 'success');
    } else {
        showToast('❌ ' + result.error, 'error');
    }
}

// =============================================================================
// EVENT LISTENERS
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            navigateToPage(item.dataset.page);
        });
    });

    // Wallet
    document.getElementById('btn-create-wallet').addEventListener('click', createWallet);
    document.getElementById('btn-check-balance').addEventListener('click', checkBalance);

    // Send
    document.getElementById('send-form').addEventListener('submit', sendTransaction);

    // Blocks
    document.getElementById('btn-search-block').addEventListener('click', searchBlock);
    document.getElementById('search-height').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchBlock();
    });

    // Mining
    document.getElementById('btn-mine').addEventListener('click', mineBlock);

    // Load dashboard on start
    loadDashboard();
});
