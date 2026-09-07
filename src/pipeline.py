"""
FaceChain Verify - End-to-end pipeline.

Pipeline:
    face scan
        -> reverse image search
        -> discover a social-media match
        -> hash + upload to blockchain
        -> re-verify against the on-chain record.

Usage from the project root:

    python main.py --image tests/sample_data/my_photo.jpg \
        --mode contract --network local
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
    upload_via_tx_data,
    verify_via_tx_data,
    upload_via_contract,
    verify_via_contract,
)


# ---------------------------------------------------------------------
# ENVIRONMENT
# ---------------------------------------------------------------------

load_dotenv()


NETWORKS = {
    "local": os.getenv(
        "LOCAL_RPC_URL",
        "http://127.0.0.1:8545",
    ),
    "sepolia": os.getenv(
        "SEPOLIA_RPC_URL",
        "",
    ),
    "amoy": os.getenv(
        "AMOY_RPC_URL",
        "",
    ),
}


# ---------------------------------------------------------------------
# WEB3 CONNECTION
# ---------------------------------------------------------------------

def get_web3(network: str) -> Web3:
    """
    Connect to the selected blockchain network.
    """

    rpc_url = NETWORKS.get(network)

    if not rpc_url:
        sys.exit(
            f"No RPC URL configured for network '{network}'. "
            f"Check your .env file."
        )

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        sys.exit(
            f"Could not connect to {network} at {rpc_url}. "
            f"Is `npx hardhat node` running (for 'local'), "
            f"or is the RPC URL correct?"
        )

    return w3


# ---------------------------------------------------------------------
# BLOCKCHAIN ACCOUNT
# ---------------------------------------------------------------------

def load_account(w3: Web3):
    """
    Load the blockchain account from PRIVATE_KEY.
    """

    private_key = os.getenv("PRIVATE_KEY")

    if not private_key:
        sys.exit(
            "Set PRIVATE_KEY in your .env file "
            "(a funded testnet/local account)."
        )

    try:
        return w3.eth.account.from_key(private_key)
    except Exception as exc:
        sys.exit(
            f"Invalid PRIVATE_KEY in .env: {exc}"
        )


# ---------------------------------------------------------------------
# CONTRACT
# ---------------------------------------------------------------------

def load_contract(w3: Web3):
    """
    Load the deployed ProofRegistry contract.
    """

    address = os.getenv("CONTRACT_ADDRESS")

    abi_path = os.getenv(
        "CONTRACT_ABI_PATH",
        os.path.join(
            "..",
            "blockchain",
            "artifacts",
            "contracts",
            "ProofRegistry.sol",
            "ProofRegistry.json",
        ),
    )

    if not address:
        sys.exit(
            "Set CONTRACT_ADDRESS in your .env file "
            "(see README '3. Deploy the contract')."
        )

    # CONTRACT_ABI_PATH is relative to this src/ directory.
    abi_path = os.path.join(
        os.path.dirname(__file__),
        abi_path,
    )

    if not os.path.exists(abi_path):
        sys.exit(
            f"Contract ABI not found at: {abi_path}"
        )

    try:
        with open(abi_path, "r") as f:
            abi = json.load(f)["abi"]
    except Exception as exc:
        sys.exit(
            f"Could not load contract ABI: {exc}"
        )

    return w3.eth.contract(
        address=address,
        abi=abi,
    )


# ---------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------

def run(
    image_path: str,
    mode: str = "contract",
    network: str = "local",
) -> dict:
    """
    Run the complete FaceChain Verify pipeline.

    Steps:
        1. Detect and encode face.
        2. Perform genuine reverse-image search and discover
           a social-media result.
        3. Hash discovered result and upload fingerprint
           to blockchain.
        4. Re-verify the fingerprint against blockchain.
    """

    # -------------------------------------------------------------
    # Validate image
    # -------------------------------------------------------------

    if not os.path.exists(image_path):
        sys.exit(
            f"Image not found: {image_path}"
        )

    # -------------------------------------------------------------
    # STEP 1: FACE DETECTION
    # -------------------------------------------------------------

    print(
        f"[1/4] Detecting face in {image_path} ..."
    )

    embedding = get_face_embedding(image_path)

    print(
        f"      -> got a {embedding.shape[0]}-dim face embedding"
    )

    # -------------------------------------------------------------
    # STEP 2: GENUINE REVERSE IMAGE SEARCH
    # -------------------------------------------------------------

    print(
        "[2/4] Running genuine reverse image search ..."
    )

    try:
        all_matches = reverse_image_search(image_path)
    except Exception as exc:
        sys.exit(
            "Reverse image search failed.\n"
            f"Error: {exc}"
        )

    print(
        f"      -> collected {len(all_matches)} "
        f"candidate web result(s)"
    )

    # Filter dynamically discovered results to social platforms.
    social_matches = filter_social_matches(
        all_matches
    )

    print(
        f"      -> found {len(social_matches)} "
        f"social-media candidate(s)"
    )

    if not social_matches:
        sys.exit(
            "No social-media matches were discovered.\n"
            "\n"
            "The pipeline requires a real result from the "
            "reverse-image search.\n"
            "Do NOT use a manually supplied URL.\n"
            "\n"
            "Make sure the test image has already been posted "
            "publicly and is indexed by the search service."
        )

    # Take the first dynamically discovered social result.
    matched = social_matches[0]

    matched_url = matched.get("url")

    if not matched_url:
        sys.exit(
            "Reverse-image search returned an invalid "
            "social-media result without a URL."
        )

    print(
        f"      -> discovered social match: {matched_url}"
    )

    if matched.get("page_title"):
        print(
            f"      -> result title: "
            f"{matched['page_title']}"
        )

    # -------------------------------------------------------------
    # STEP 3: HASH + BLOCKCHAIN UPLOAD
    # -------------------------------------------------------------

    print(
        "[3/4] Hashing + uploading to blockchain ..."
    )

    # The fingerprint binds:
    #   image bytes + dynamically discovered URL
    fingerprint = compute_fingerprint(
        image_path,
        matched_url,
    )

    print(
        f"      -> fingerprint: {fingerprint}"
    )

    # Connect to blockchain.
    w3 = get_web3(network)

    # Load account.
    account = load_account(w3)

    record_id = None

    if mode == "tx":

        tx_hash = upload_via_tx_data(
            w3,
            account,
            fingerprint,
        )

    else:

        contract = load_contract(w3)

        tx_hash, record_id = upload_via_contract(
            w3,
            account,
            contract,
            fingerprint,
            matched_url,
        )

    print(
        f"      -> tx: {tx_hash}"
        + (
            f"  (record id {record_id})"
            if record_id is not None
            else ""
        )
    )

    # -------------------------------------------------------------
    # STEP 4: RE-VERIFY
    # -------------------------------------------------------------

    print(
        "[4/4] Re-verifying against the on-chain record ..."
    )

    if mode == "tx":

        verified = verify_via_tx_data(
            w3,
            tx_hash,
            fingerprint,
        )

    else:

        verified = verify_via_contract(
            contract,
            record_id,
            fingerprint,
        )

    print(
        f"      -> VERIFIED: {verified}"
    )

    # -------------------------------------------------------------
    # RETURN RESULT
    # -------------------------------------------------------------

    return {
        "matched_url": matched_url,
        "fingerprint": fingerprint,
        "tx_hash": tx_hash,
        "record_id": record_id,
        "verified": verified,
    }


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "FaceChain Verify: "
            "face scan -> reverse image search -> "
            "blockchain verification"
        )
    )

    parser.add_argument(
        "--image",
        required=True,
        help="Path to the face scan image",
    )

    parser.add_argument(
        "--mode",
        choices=["tx", "contract"],
        default="contract",
        help="Blockchain storage mode",
    )

    parser.add_argument(
        "--network",
        choices=["local", "sepolia", "amoy"],
        default="local",
        help="Blockchain network",
    )

    args = parser.parse_args()

    result = run(
        args.image,
        args.mode,
        args.network,
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )