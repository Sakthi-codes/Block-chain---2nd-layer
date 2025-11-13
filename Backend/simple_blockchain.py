#!/usr/bin/env python3
"""
Simple blockchain implementation (educational).
Run: pip install flask requests
Then: python simple_blockchain.py
"""

import hashlib
import json
import time
from urllib.parse import urlparse
from uuid import uuid4
from typing import List, Dict, Any
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# --- Configuration ---
DIFFICULTY = 4  # number of leading zeros required in PoW hash (in hex). Increase to make mining harder.

# --- Blockchain class ---
class Blockchain:
    def __init__(self):
        self.chain: List[Dict[str, Any]] = []
        self.current_transactions: List[Dict[str, Any]] = []
        self.nodes = set()

        # Create the genesis block
        self.new_block(proof=100, previous_hash="1")

    def register_node(self, address: str):
        """
        Add a new node's address (e.g. 'http://127.0.0.1:5001')
        """
        parsed = urlparse(address)
        if parsed.netloc:
            self.nodes.add(parsed.netloc)
        elif parsed.path:
            # Accept addresses without scheme like '127.0.0.1:5001'
            self.nodes.add(parsed.path)
        else:
            raise ValueError("Invalid node URL")

    def valid_chain(self, chain: List[Dict[str, Any]]) -> bool:
        """
        Determine if a given blockchain is valid:
        - hashes link up
        - proofs are valid according to PoW rules
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the proof is valid
            if not self.valid_proof(last_block['proof'], block['proof'], last_block['previous_hash'] if 'previous_hash' in last_block else self.hash(last_block)):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self) -> bool:
        """
        Consensus algorithm: replace chain with the longest one in the network if valid.
        Returns True if our chain was replaced.
        """
        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbours:
            try:
                resp = requests.get(f'http://{node}/chain', timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    length = data['length']
                    chain = data['chain']
                    if length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain
            except requests.RequestException:
                # couldn't reach node — skip
                continue

        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof: int, previous_hash: str = None) -> Dict[str, Any]:
        """
        Create a new Block in the Blockchain
        """
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender: str, recipient: str, amount: float) -> int:
        """
        Creates a new transaction to go into the next mined Block.
        Returns the index of the block that will hold this transaction.
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block: Dict[str, Any]) -> str:
        """
        Creates a SHA-256 hash of a Block (after sorting keys).
        """
        # We must ensure the dictionary is ordered to produce consistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self) -> Dict[str, Any]:
        return self.chain[-1]

    def proof_of_work(self, last_proof: int, last_hash: str) -> int:
        """
        Simple Proof of Work:
        - Find a number p such that hash(last_proof, p, last_hash) has DIFFICULTY leading zeros.
        """
        proof = 0
        target = '0' * DIFFICULTY
        while not self.valid_proof(last_proof, proof, last_hash, target):
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof: int, proof: int, last_hash: str, target: str = None) -> bool:
        """
        Validates the proof: does hash(last_proof, proof, last_hash) start with DIFFICULTY zeroes?
        """
        if target is None:
            target = '0' * DIFFICULTY
        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:len(target)] == target


# --- Flask app (API) ---
app = Flask(__name__)
CORS(app)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    # We run proof of work to get the next proof...
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    last_hash = blockchain.hash(last_block)
    proof = blockchain.proof_of_work(last_proof, last_hash)

    # Reward the miner (this node) with a transaction. "0" means new coin has been mined.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    block = blockchain.new_block(proof, previous_hash=last_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not values:
        return 'Missing JSON body', 400
    if not all(k in values for k in required):
        return 'Missing values', 400

    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    return jsonify({'message': f'Transaction will be added to Block {index}'}), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    return jsonify({
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    if not values:
        return "Error: Please supply a JSON body", 400
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Missing 'nodes' field", 400
    for node in nodes:
        try:
            blockchain.register_node(node)
        except ValueError:
            continue
    return jsonify({
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        return jsonify({
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }), 200
    else:
        return jsonify({
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }), 200

if __name__ == '__main__':
    # Example: set FLASK_ENV=development for reloader during development
    app.run(host='0.0.0.0', port=5000)