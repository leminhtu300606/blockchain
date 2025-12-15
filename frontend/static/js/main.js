// Main JavaScript for the blockchain explorer
document.addEventListener('DOMContentLoaded', function() {
    // Initialize any global functionality here
    console.log('Blockchain Explorer initialized');
    
    // Add any common JavaScript functionality here
    // For example, handling navigation active states
    const currentPath = window.location.pathname;
    document.querySelectorAll('nav a').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('font-bold', 'border-b-2', 'border-white');
        }
    });
});

// Utility functions
function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString();
}

function formatHash(hash, length = 8) {
    if (!hash) return '';
    if (hash.length <= length * 2) return hash;
    return `${hash.substring(0, length)}...${hash.substring(hash.length - length)}`;
}

// Export functions for use in other modules
window.BlockchainUtils = {
    formatTimestamp,
    formatHash
};
