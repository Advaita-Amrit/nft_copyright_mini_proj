# blockchain.py
"""
Blockchain helper for local dev:
- compiles & deploys a simple ERC721-like contract
- mints tokens and stores a watermark hash
- returns tx info and token id (if available)

Designed for local development (Ganache). Not production-audited.
"""

import json
import base64
import os
from web3 import Web3
from solcx import compile_standard, install_solc
from eth_account import Account
from time import sleep

SOLC_VERSION = "0.8.20"

# Minimal ERC721-like contract (fallback) to avoid import issues offline
MINIMAL_ERC721 = r"""
// Minimal ERC721 + URI storage to avoid OpenZeppelin dependency at compile-time.
// NOTE: Simplified for development. Use OpenZeppelin in production.
pragma solidity ^0.8.0;

contract SimpleERC721 {
    string private _name;
    string private _symbol;

    mapping(uint256 => address) private _owners;
    mapping(address => uint256) private _balances;
    mapping(uint256 => string) private _tokenURIs;

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);

    constructor(string memory name_, string memory symbol_) {
        _name = name_;
        _symbol = symbol_;
    }

    function _safeMint(address to, uint256 tokenId) internal virtual {
        require(to != address(0), "mint to zero");
        require(_owners[tokenId] == address(0), "already minted");
        _balances[to] += 1;
        _owners[tokenId] = to;
        emit Transfer(address(0), to, tokenId);
    }

    function _setTokenURI(uint256 tokenId, string memory _uri) internal virtual {
        _tokenURIs[tokenId] = _uri;
    }

    function ownerOf(uint256 tokenId) public view virtual returns (address) {
        return _owners[tokenId];
    }
}
"""

CONTRACT_SOURCE = MINIMAL_ERC721 + """

contract WatermarkNFT is SimpleERC721 {
    uint256 public nextTokenId;
    mapping(uint256 => string) public watermarkHash; // store SHA256 hash

    event Minted(uint256 indexed tokenId, address indexed to, string watermarkHash);

    constructor(string memory name_, string memory symbol_) SimpleERC721(name_, symbol_) {
        nextTokenId = 1;
    }

    function mint(address to, string memory tokenURI_, string memory wmHash) external returns (uint256) {
        uint256 tokenId = nextTokenId;
        nextTokenId = nextTokenId + 1;
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, tokenURI_);
        watermarkHash[tokenId] = wmHash;
        emit Minted(tokenId, to, wmHash);
        return tokenId;
    }

    function getWatermarkHash(uint256 tokenId) external view returns (string memory) {
        return watermarkHash[tokenId];
    }
}
"""

def _ensure_solc():
    try:
        install_solc(SOLC_VERSION)
    except Exception:
        # ignore if already installed or if install fails; compile may still work
        pass

def metadata_to_data_uri(metadata: dict) -> str:
    """Convert metadata dict to data:application/json;base64,<base64json>"""
    json_str = json.dumps(metadata, separators=(",", ":"), ensure_ascii=False)
    b64 = base64.b64encode(json_str.encode()).decode()
    return f"data:application/json;base64,{b64}"

class BlockchainClient:
    def __init__(self, rpc_url: str, private_key: str, chain_id: int = None):
        self.rpc_url = rpc_url or os.environ.get("RPC_URL", "http://127.0.0.1:7545")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to RPC at {self.rpc_url}")

        self.private_key = private_key or os.environ.get("PRIVATE_KEY")
        if not self.private_key:
            raise ValueError("PRIVATE_KEY required (env var or parameter).")
        self.account = Account.from_key(self.private_key)
        self.address = self.account.address
        if chain_id:
            self.chain_id = chain_id
        else:
            try:
                self.chain_id = int(self.w3.eth.chain_id)
            except Exception:
                self.chain_id = 1337

        self.contract = None
        self.contract_address = None
        self.compiled = None

    def compile_and_deploy(self, name="WatermarkNFT", symbol="WMT", force_redeploy=False):
        if self.contract is not None and not force_redeploy:
            return self.contract, self.contract_address

        _ensure_solc()
        compiled = compile_standard({
            "language": "Solidity",
            "sources": {"WatermarkNFT.sol": {"content": CONTRACT_SOURCE}},
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": ["abi", "evm.bytecode.object"]
                    }
                }
            }
        }, solc_version=SOLC_VERSION)

        contract_data = compiled['contracts']['WatermarkNFT.sol']
        contract_name = next(iter(contract_data.keys()))
        abi = contract_data[contract_name]['abi']
        bytecode = contract_data[contract_name]['evm']['bytecode']['object']

        contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)

        nonce = self.w3.eth.get_transaction_count(self.address)
        construct_txn = contract.constructor(name, symbol).build_transaction({
            'from': self.address,
            'nonce': nonce,
            'gas': 6_000_000,
            'gasPrice': self.w3.to_wei('20', 'gwei'),
            'chainId': self.chain_id
        })

        signed = self.account.sign_transaction(construct_txn)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        self.contract_address = tx_receipt.contractAddress
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=abi)
        self.compiled = compiled
        return self.contract, self.contract_address

    def load_contract(self, address: str, abi: dict):
        self.contract = self.w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)
        self.contract_address = address
        return self.contract

    def mint_nft(self, to_address: str, token_uri: str, watermark_hash: str):
        if self.contract is None:
            raise RuntimeError("Contract not deployed or loaded. Call compile_and_deploy() first.")

        nonce = self.w3.eth.get_transaction_count(self.address)
        tx = self.contract.functions.mint(
            Web3.to_checksum_address(to_address),
            token_uri,
            watermark_hash
        ).build_transaction({
            'from': self.address,
            'nonce': nonce,
            'gas': 500000,
            'gasPrice': self.w3.to_wei('20', 'gwei'),
            'chainId': self.chain_id
        })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

        token_id = None
        try:
            logs = self.contract.events.Minted().processReceipt(tx_receipt)
            if logs and len(logs) > 0:
                token_id = logs[0]['args']['tokenId']
        except Exception:
            # best-effort: if event parsing fails, token_id may still be retrievable externally
            pass

        return {
            "tx_hash": tx_receipt.transactionHash.hex(),
            "tx_receipt": tx_receipt,
            "token_id": token_id
        }

    def get_token_owner(self, token_id: int):
        if self.contract is None:
            raise RuntimeError("Contract not deployed or loaded.")
        try:
            return self.contract.functions.ownerOf(token_id).call()
        except Exception:
            return None

    def get_watermark_hash(self, token_id: int):
        if self.contract is None:
            raise RuntimeError("Contract not deployed or loaded.")
        try:
            return self.contract.functions.getWatermarkHash(token_id).call()
        except Exception:
            return None
