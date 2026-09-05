"""
End-to-end pipeline:
  face scan -> reverse image search -> pick a social match -> hash + upload
  to chain -> re-verify against the on-chain record.

Usage (from the project root):
  python main.py --image path/to/photo.jpg --mode contract --network local
  python main.py --image path/to/photo.jpg --mode tx       --network sepolia
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from web3 import Web3

from face_module import get_face_embedding
from social_search import reverse_image_search, filter_social_matches
from blockchain_verify import (
    compute_fingerprint,
    upload_via_tx_data, verify_via_tx_data,
    upload_via_contract, verify_via_contract,
)

load_dotenv()

NETWORKS = {
    "local": os.getenv("LOCAL_RPC_URL", "http://127.0.0.1:8545"),
    "sepolia": os.getenv("SEPOLIA_RPC_URL", ""),
    "amoy": os.getenv("AMOY_RPC_URL", ""),
}


def get_web3(network: str) -> Web3:
    rpc_url = NETWORKS.get(network)
    if not rpc_url:
        sys.exit(f"No RPC URL configured for network '{network}'. Check your .env file.")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        sys.exit(f"Could not connect to {network} at {rpc_url}. "
                  f"Is `npx hardhat node` running (for 'local'), or is the RPC URL correct?")
    return w3


def load_account(w3: Web3):
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        sys.exit("Set PRIVATE_KEY in your .env file (a funded testnet/local account).")
    return w3.eth.account.from_key(private_key)


def load_contract(w3: Web3):
    address = os.getenv("CONTRACT_ADDRESS")
    abi_path = os.getenv(
        "CONTRACT_ABI_PATH",
        os.path.join("..", "blockchain", "artifacts", "contracts", "ProofRegistry.sol", "ProofRegistry.json"),
    )
    if not address:
        sys.exit("Set CONTRACT_ADDRESS in your .env file (see README '3. Deploy the contract').")
    abi_path = os.path.join(os.path.dirname(__file__), abi_path)
    with open(abi_path) as f:
        abi = json.load(f)["abi"]
    return w3.eth.contract(address=address, abi=abi)


def run(image_path: str, mode: str = "contract", network: str = "local") -> dict:
    print(f"[1/4] Detecting face in {image_path} ...")
    embedding = get_face_embedding(image_path)
    print(f"      -> got a {embedding.shape[0]}-dim face embedding")

    print("[2/4] Running reverse image search ...")
    all_matches = reverse_image_search(image_path)
    social_matches = filter_social_matches(all_matches)
    if not social_matches:
        sys.exit(
            "No social media matches found for this image.\n"
            "This is expected the first time: reverse image search only finds photos\n"
            "that are ALREADY public somewhere Google has indexed. Use a photo you've\n"
            "actually posted publicly before (e.g. a profile picture), or post a test\n"
            "photo publicly first and give it a day or two to get indexed."
        )

    matched = social_matches[0]
    print(f"      -> found social match: {matched['url']}")

    print("[3/4] Hashing + uploading to blockchain ...")
    fingerprint = compute_fingerprint(image_path, matched["url"])
    w3 = get_web3(network)
    account = load_account(w3)

    record_id = None
    if mode == "tx":
        tx_hash = upload_via_tx_data(w3, account, fingerprint)
    else:
        contract = load_contract(w3)
        tx_hash, record_id = upload_via_contract(w3, account, contract, fingerprint, matched["url"])
    print(f"      -> tx: {tx_hash}" + (f"  (record id {record_id})" if record_id is not None else ""))

    print("[4/4] Re-verifying against the on-chain record ...")
    if mode == "tx":
        verified = verify_via_tx_data(w3, tx_hash, fingerprint)
    else:
        verified = verify_via_contract(contract, record_id, fingerprint)
    print(f"      -> VERIFIED: {verified}")

    return {
        "matched_url": matched["url"],
        "fingerprint": fingerprint,
        "tx_hash": tx_hash,
        "record_id": record_id,
        "verified": verified,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Path to the face scan image")
    parser.add_argument("--mode", choices=["tx", "contract"], default="contract")
    parser.add_argument("--network", choices=["local", "sepolia", "amoy"], default="local")
    args = parser.parse_args()

    result = run(args.image, args.mode, args.network)
    print(json.dumps(result, indent=2))
