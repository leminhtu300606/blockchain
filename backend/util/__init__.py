"""
Util Package - Utility Functions cho Blockchain

Package này export các functions và classes tiện ích:

Transaction Utilities (tx_utils):
- generate_keypair(): Tạo keypair mới
- create_p2pkh_script(): Tạo P2PKH locking script
- sign_transaction(): Ký transaction input
- verify_transaction(): Verify signatures
- create_signed_transaction(): Tạo và ký transaction
- debug_print_transaction(): Print transaction details

Block Utilities (block_utils):
- BlockBuilder: Builder class để tạo blocks
- create_genesis_block(): Tạo genesis block
- add_transactions_to_block(): Thêm txs vào block
- BlockCreationError: Exception cho lỗi tạo block

Merkle Tree (merkle):
- calculate_merkle_root(): Tính merkle root
- verify_merkle_proof(): Verify merkle proof
- get_merkle_path(): Lấy proof path

Hash Functions (util):
- hash256(): Double SHA-256
- hash160(): RIPEMD160(SHA256())
- sha256(): Single SHA-256
"""

from .tx_utils import (
    generate_keypair,
    sign_transaction,
    create_signed_transaction,
    debug_print_transaction,
    DebugTransactionError
)

from core.transaction_verifier import (
    verify_transaction,
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

from .util import (
    hash256,
    hash160,
    sha256
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
    'get_merkle_path',
    
    # Hash functions
    'hash256',
    'hash160',
    'sha256'
]