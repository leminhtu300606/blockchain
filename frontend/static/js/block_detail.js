document.addEventListener('DOMContentLoaded', function() {
    // Add copy functionality to hash and addresses
    const copyButtons = document.querySelectorAll('.copy-btn');
    
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.getAttribute('data-copy');
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalText = this.textContent;
                this.textContent = 'Copied!';
                this.classList.add('bg-green-500');
                
                setTimeout(() => {
                    this.textContent = originalText;
                    this.classList.remove('bg-green-500');
                }, 2000);
            });
        });
    });

    // Add expand/collapse functionality for transaction details
    const transactionToggles = document.querySelectorAll('.transaction-toggle');
    
    transactionToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const details = this.nextElementSibling;
            details.classList.toggle('hidden');
            this.querySelector('svg').classList.toggle('transform');
            this.querySelector('svg').classList.toggle('rotate-180');
        });
    });

    // Update confirmation count every minute
    if (document.getElementById('confirmations')) {
        setInterval(updateConfirmations, 60000);
    }
});

function updateConfirmations() {
    const confirmationsElement = document.getElementById('confirmations');
    if (confirmationsElement) {
        let confirmations = parseInt(confirmationsElement.textContent);
        confirmationsElement.textContent = confirmations + 1;
    }
}

// Format large numbers with commas
function formatNumber(number) {
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Format timestamp to relative time
function formatTimeAgo(timestamp) {
    const seconds = Math.floor((new Date() - new Date(timestamp)) / 1000);
    let interval = Math.floor(seconds / 31536000);
    
    if (interval >= 1) {
        return interval + ' year' + (interval === 1 ? '' : 's') + ' ago';
    }
    interval = Math.floor(seconds / 2592000);
    if (interval >= 1) {
        return interval + ' month' + (interval === 1 ? '' : 's') + ' ago';
    }
    interval = Math.floor(seconds / 86400);
    if (interval >= 1) {
        return interval + ' day' + (interval === 1 ? '' : 's') + ' ago';
    }
    interval = Math.floor(seconds / 3600);
    if (interval >= 1) {
        return interval + ' hour' + (interval === 1 ? '' : 's') + ' ago';
    }
    interval = Math.floor(seconds / 60);
    if (interval >= 1) {
        return interval + ' minute' + (interval === 1 ? '' : 's') + ' ago';
    }
    return Math.floor(seconds) + ' seconds ago';
}
