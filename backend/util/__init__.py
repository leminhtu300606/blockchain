"""
Utility modules for the blockchain.
This package contains various utility functions and classes for transaction and block handling.
"""

from .tx_utils import (
    generate_keypair,
    create_p2pkh_script,
    sign_transaction,
    verify_transaction,
    create_signed_transaction,
    debug_print_transaction,
    DebugTransactionError
)

from .block_utils import (
    BlockBuilder,
    create_genesis_block,
    add_transactions_to_block,
    BlockCreationError
)

from .merkle import (
    calculate_merkle_root,
    verify_merkle_proof,
    get_merkle_path
)

__all__ = [
    # Transaction utilities
    'generate_keypair',
    'create_p2pkh_script',
    'sign_transaction',
    'verify_transaction',
    'create_signed_transaction',
    'debug_print_transaction',
    'DebugTransactionError',
    
    # Block utilities
    'BlockBuilder',
    'create_genesis_block',
    'add_transactions_to_block',
    'BlockCreationError',
    
    # Merkle tree utilities
    'calculate_merkle_root',
    'verify_merkle_proof',
    'get_merkle_path'
]