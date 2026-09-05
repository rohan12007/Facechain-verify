"""
Blockchain upload + verification step.

Two write paths are provided:

1. upload_via_tx_data / verify_via_tx_data
   No smart contract needed. The fingerprint hash is written straight into
   a self-send transaction's `data` field. Works on any EVM chain (local
   Hardhat node, Sepolia, Polygon Amoy, ...). Fastest to get working.

2. upload_via_contract / verify_via_contract
   Calls ProofRegistry.submitProof() on the contract in
   blockchain/contracts/ProofRegistry.sol. Gives you a queryable on-chain
   record and an event log -- nicer for a demo/recording because you can
   show the record living at a specific id, not just buried in tx calldata.

Both paths are "verified" the same way: re-derive the fingerprint from the
original inputs, pull the previously-stored value back off the chain, and
compare the two.
"""

import hashlib
import json
from typing import Optional, Tuple

from web3 import Web3


def compute_fingerprint(image_path: str, matched_url: str, extra: Optional[dict] = None) -> str:
    """SHA-256 fingerprint over the image bytes + the matched post URL
    (+ any extra metadata you want bound into the proof, e.g. a timestamp).
    Returns a 64-char hex string (32 bytes)."""
    h = hashlib.sha256()
    with open(image_path, "rb") as f:
        h.update(f.read())
    h.update(matched_url.encode("utf-8"))
    if extra:
        h.update(json.dumps(extra, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


# ---------- Path 1: no contract, just a tx with a data payload ----------

def upload_via_tx_data(w3: Web3, account, fingerprint_hex: str) -> str:
    tx = {
        "from": account.address,
        "to": account.address,
        "value": 0,
        "data": "0x" + fingerprint_hex,
        "nonce": w3.eth.get_transaction_count(account.address),
        "chainId": w3.eth.chain_id,
    }
    tx["gas"] = w3.eth.estimate_gas(tx)
    tx["gasPrice"] = w3.eth.gas_price

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt.transactionHash.hex()


def verify_via_tx_data(w3: Web3, tx_hash: str, expected_fingerprint_hex: str) -> bool:
    tx = w3.eth.get_transaction(tx_hash)
    onchain_hex = tx["input"].hex()
    onchain_hex = onchain_hex[2:] if onchain_hex.startswith("0x") else onchain_hex
    return onchain_hex.lower() == expected_fingerprint_hex.lower()


# ---------- Path 2: via the ProofRegistry smart contract ----------

def upload_via_contract(
    w3: Web3, account, contract, fingerprint_hex: str, matched_url: str
) -> Tuple[str, Optional[int]]:
    fingerprint_bytes32 = bytes.fromhex(fingerprint_hex)
    tx = contract.functions.submitProof(fingerprint_bytes32, matched_url).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "chainId": w3.eth.chain_id,
    })
    tx["gas"] = w3.eth.estimate_gas(tx)
    tx["gasPrice"] = w3.eth.gas_price

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    logs = contract.events.ProofSubmitted().process_receipt(receipt)
    record_id = logs[0]["args"]["id"] if logs else None
    return receipt.transactionHash.hex(), record_id


def verify_via_contract(contract, record_id: int, expected_fingerprint_hex: str) -> bool:
    fingerprint_bytes32 = bytes.fromhex(expected_fingerprint_hex)
    return contract.functions.verify(record_id, fingerprint_bytes32).call()
