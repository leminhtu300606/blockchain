import socket
import threading
import json
import logging
import time
from typing import List, Set

logger = logging.getLogger(__name__)

class P2PNode:
    """
    P2P Node - Quản lý kết nối và lan truyền dữ liệu trong mạng.
    """
    def __init__(self, host: str, port: int, blockchain):
        self.host = host
        self.port = port
        self.blockchain = blockchain
        self.peers: Set[tuple] = set()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True

    def start_server(self):
        """Bắt đầu lắng nghe kết nối từ các node khác."""
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        logger.info(f"P2P Node listening on {self.host}:{self.port}")
        
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        while self.running:
            try:
                conn, addr = self.socket.accept()
                logger.debug(f"New connection from {addr}")
                threading.Thread(target=self._handle_peer, args=(conn, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")

    def _handle_peer(self, conn, addr):
        with conn:
            while self.running:
                try:
                    data = conn.recv(65536)
                    if not data:
                        break
                    
                    message = json.loads(data.decode('utf-8'))
                    self._process_message(message, addr)
                except Exception as e:
                    logger.error(f"Error handling peer {addr}: {e}")
                    break

    def _process_message(self, message: dict, addr: tuple):
        msg_type = message.get('type')
        payload = message.get('data')
        
        if msg_type == 'NEW_BLOCK':
            logger.info(f"Received new block from {addr}")
            # Logic: verify and add block to chain
            if self.blockchain.receive_block(payload):
                 logger.info(f"Block accepted and added to chain")
            else:
                 logger.warning(f"Block rejected")
        elif msg_type == 'NEW_TX':
            logger.info(f"Received new transaction from {addr}")
            # Logic: verify and add to mempool
            pass
        elif msg_type == 'ADDRESS':
            new_peer = tuple(payload)
            if new_peer != (self.host, self.port):
                self.peers.add(new_peer)

    def connect_to_peer(self, host: str, port: int):
        """Kết nối đến một node khác."""
        try:
            peer_addr = (host, port)
            if peer_addr == (self.host, self.port):
                return
            
            with socket.create_connection(peer_addr, timeout=5) as conn:
                self.peers.add(peer_addr)
                # Lan truyền địa chỉ của mình
                msg = {'type': 'ADDRESS', 'data': [self.host, self.port]}
                conn.sendall(json.dumps(msg).encode('utf-8'))
                logger.info(f"Connected to peer {peer_addr}")
        except Exception as e:
            logger.warning(f"Failed to connect to peer {host}:{port}: {e}")

    def broadcast(self, message: dict):
        """Gửi thông điệp đến tất cả các peers."""
        data = json.dumps(message).encode('utf-8')
        for peer in list(self.peers):
            try:
                with socket.create_connection(peer, timeout=2) as conn:
                    conn.sendall(data)
            except Exception:
                logger.debug(f"Peer {peer} unreachable, removing...")
                self.peers.remove(peer)

    def stop(self):
        self.running = False
        self.socket.close()
