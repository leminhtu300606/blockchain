import sys
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.blockchain import Blockchain
    from api.transaction_api import tx_api
    from api.history_api import history_api
    from core.p2p_node import P2PNode
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# Configure Loggings
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app)
    
    # Initialize Blockchain
    try:
        blockchain = Blockchain()
        app.blockchain = blockchain
        logger.info(f"Blockchain initialized. Height: {blockchain.get_chain_height()}")
        
        # Initialize and Start P2P Node
        p2p_port = int(os.environ.get("P2P_PORT", 6000))
        p2p_node = P2PNode('0.0.0.0', p2p_port, blockchain)
        p2p_node.start_server()
        app.p2p_node = p2p_node
        
        # Connect to seed node if provided
        seed_node = os.environ.get("SEED_NODE")
        if seed_node:
            host, port = seed_node.split(':')
            p2p_node.connect_to_peer(host, int(port))
            
    except Exception as e:
        logger.error(f"Failed to initialize blockchain or P2P: {e}")
        
    # Register Blueprints
    app.register_blueprint(tx_api, url_prefix='/api/transaction')
    app.register_blueprint(history_api, url_prefix='/api/history')
    
    @app.route('/')
    def index():
        return jsonify({
            "service": "Blockchain Backend API",
            "status": "running",
            "endpoints": [
                "/api/transaction/verify",
                "/api/transaction/verify/coinbase"
            ]
        })
        
    @app.route('/chain')
    def get_chain():
        """Helper endpoint to view the whole chain"""
        # Note: In production this might be too large
        return jsonify(app.blockchain.db.read())

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Backend Server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
