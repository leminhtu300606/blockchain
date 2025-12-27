// Main JavaScript for Blockchain Ecosystem
document.addEventListener('DOMContentLoaded', function () {
    console.log('Blockchain Protocol UI Initialized');

    // Handle Navigation Active States
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('text-white', 'font-bold');
            link.classList.remove('text-gray-300');
        }
    });

    // Mining Control Logic
    const miningBtn = document.getElementById('start-mining-btn');
    if (miningBtn) {
        let isMining = false;
        miningBtn.addEventListener('click', async () => {
            isMining = !isMining;

            // UI Feedback
            if (isMining) {
                showToast('🚀 Mining started!', 'success');
                miningBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Stop Miner';
                miningBtn.classList.remove('text-purple-400', 'border-purple-500/30');
                miningBtn.classList.add('text-red-400', 'border-red-500/30', 'bg-red-400/5');
            } else {
                showToast('⏹️ Miner stopped', 'info');
                miningBtn.innerHTML = 'Start Miner';
                miningBtn.classList.add('text-purple-400', 'border-purple-500/30');
                miningBtn.classList.remove('text-red-400', 'border-red-500/30', 'bg-red-400/5');
            }

            try {
                const response = await fetch('/api/mining/control', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: isMining ? 'start' : 'stop' })
                });
                const data = await response.json();
                console.log('Mining status:', data.status);
            } catch (error) {
                console.error('Failed to control mining:', error);
                showToast('❌ Failed to connect to mining server', 'error');
            }
        });
    }
});

// Toast System
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast';

    let icon = '<i class="fas fa-info-circle text-blue-400"></i>';
    if (type === 'success') icon = '<i class="fas fa-check-circle text-green-400"></i>';
    if (type === 'error') icon = '<i class="fas fa-times-circle text-red-400"></i>';

    toast.innerHTML = `${icon} <span class="text-sm font-medium">${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Global copy utility
function copyToClipboard(id) {
    const el = document.getElementById(id);
    const text = el.innerText || el.value;
    navigator.clipboard.writeText(text).then(() => {
        showToast('✅ Copied to clipboard!', 'success');
    }).catch(err => {
        showToast('❌ Failed to copy', 'error');
    });
}

window.BlockchainUtils = {
    showToast,
    copyToClipboard
};
