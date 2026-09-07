"""
Blockchain upload + verification step.

Two write paths are provided:

1. upload_via_tx_data / verify_via_tx_data
   No smart contract needed. The fingerprint hash is written straight into
   a self-send transaction's data field.

2. upload_via_contract / verify_via_contract
   Calls ProofRegistry.submitProof() on the contract.

Both paths verify that the fingerprint stored on-chain matches the
fingerprint generated locally.
"""

import hashlib
import json
from typing import Optional, Tuple

from web3 import Web3


def compute_fingerprint(
    image_path: str,
    matched_url: str,
    extra: Optional[dict] = None
) -> str:
    """
    SHA-256 fingerprint over image bytes + matched post URL.

    Returns a 64-character hexadecimal string (32 bytes).
    """

    h = hashlib.sha256()

    with open(image_path, "rb") as f:
        h.update(f.read())

    h.update(matched_url.encode("utf-8"))

    if extra:
        h.update(
            json.dumps(
                extra,
                sort_keys=True
            ).encode("utf-8")
        )

    return h.hexdigest()


# ---------------------------------------------------------------------
# PATH 1: NO CONTRACT
# ---------------------------------------------------------------------

def upload_via_tx_data(
    w3: Web3,
    account,
    fingerprint_hex: str
) -> str:

    tx = {
        "from": account.address,
        "to": account.address,
        "value": 0,
        "data": "0x" + fingerprint_hex,
        "nonce": w3.eth.get_transaction_count(
            account.address
        ),
        "chainId": w3.eth.chain_id,
        "maxFeePerGas": w3.to_wei(
            2,
            "gwei"
        ),
        "maxPriorityFeePerGas": w3.to_wei(
            1,
            "gwei"
        ),
    }

    tx["gas"] = w3.eth.estimate_gas(tx)

    signed = account.sign_transaction(tx)

    tx_hash = w3.eth.send_raw_transaction(
        signed.rawTransaction
    )

    receipt = w3.eth.wait_for_transaction_receipt(
        tx_hash
    )

    return receipt.transactionHash.hex()


def verify_via_tx_data(
    w3: Web3,
    tx_hash: str,
    expected_fingerprint_hex: str
) -> bool:

    tx = w3.eth.get_transaction(
        tx_hash
    )

    onchain_hex = tx["input"].hex()

    if onchain_hex.startswith("0x"):
        onchain_hex = onchain_hex[2:]

    return (
        onchain_hex.lower()
        == expected_fingerprint_hex.lower()
    )


# ---------------------------------------------------------------------
# PATH 2: PROOFREGISTRY SMART CONTRACT
# ---------------------------------------------------------------------

def upload_via_contract(
    w3: Web3,
    account,
    contract,
    fingerprint_hex: str,
    matched_url: str
) -> Tuple[str, int]:
    """
    Submit a fingerprint to ProofRegistry.

    Your ProofRegistry contract does:

        records.push(...)
        id = records.length - 1
        emit ProofSubmitted(id, ...)

    Therefore the record ID can be obtained from the event.
    If event decoding is unavailable, totalRecords() provides a
    reliable fallback because the new record is always the last one.
    """

    fingerprint_bytes32 = bytes.fromhex(
        fingerprint_hex
    )

    # -------------------------------------------------------------
    # Build transaction
    # -------------------------------------------------------------

    tx = contract.functions.submitProof(
        fingerprint_bytes32,
        matched_url
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(
            account.address
        ),
        "chainId": w3.eth.chain_id,
        "maxFeePerGas": w3.to_wei(
            2,
            "gwei"
        ),
        "maxPriorityFeePerGas": w3.to_wei(
            1,
            "gwei"
        ),
    })

    tx["gas"] = w3.eth.estimate_gas(tx)

    # -------------------------------------------------------------
    # Sign + send transaction
    # -------------------------------------------------------------

    signed = account.sign_transaction(tx)

    tx_hash = w3.eth.send_raw_transaction(
        signed.rawTransaction
    )

    receipt = w3.eth.wait_for_transaction_receipt(
        tx_hash
    )

    tx_hash_hex = receipt.transactionHash.hex()

    print(
        f"      -> transaction confirmed: {tx_hash_hex}"
    )

    # -------------------------------------------------------------
    # Get record ID from ProofSubmitted event
    # -------------------------------------------------------------

    record_id = None

    try:

        logs = contract.events.ProofSubmitted().process_receipt(
            receipt
        )

        if logs:

            record_id = int(
                logs[0]["args"]["id"]
            )

            print(
                f"      -> record id from event: "
                f"{record_id}"
            )

    except Exception as exc:

        print(
            f"      -> event decoding warning: {exc}"
        )

    # -------------------------------------------------------------
    # Fallback using totalRecords()
    # -------------------------------------------------------------

    if record_id is None:

        try:

            total_records = int(
                contract.functions.totalRecords().call()
            )

            if total_records <= 0:

                raise RuntimeError(
                    "ProofRegistry reports zero records "
                    "after a successful submitProof transaction."
                )

            record_id = total_records - 1

            print(
                f"      -> record id from totalRecords(): "
                f"{record_id}"
            )

        except Exception as exc:

            raise RuntimeError(
                "Blockchain transaction succeeded, but the "
                "ProofRegistry record ID could not be determined. "
                f"totalRecords() lookup failed: {exc}"
            ) from exc

    # -------------------------------------------------------------
    # Verify that the record actually exists
    # -------------------------------------------------------------

    try:

        stored = contract.functions.getRecord(
            record_id
        ).call()

        stored_fingerprint = stored[0]

        if isinstance(
            stored_fingerprint,
            bytes
        ):
            stored_fingerprint_hex = (
                stored_fingerprint.hex()
            )
        else:
            stored_fingerprint_hex = str(
                stored_fingerprint
            )

        stored_fingerprint_hex = (
            stored_fingerprint_hex
            .replace("0x", "")
            .lower()
        )

        if (
            stored_fingerprint_hex
            != fingerprint_hex.lower()
        ):

            raise RuntimeError(
                "Blockchain record was created, but the "
                "stored fingerprint does not match the "
                "fingerprint submitted by the pipeline."
            )

        print(
            "      -> on-chain record confirmed"
        )

    except Exception as exc:

        raise RuntimeError(
            f"Unable to confirm ProofRegistry record "
            f"{record_id}: {exc}"
        ) from exc

    return (
        tx_hash_hex,
        record_id
    )


def verify_via_contract(
    contract,
    record_id: int,
    expected_fingerprint_hex: str
) -> bool:
    """
    Re-verify the fingerprint against the specified
    ProofRegistry record.
    """

    if record_id is None:

        raise ValueError(
            "record_id is None. "
            "Cannot call verify(uint256,bytes32) "
            "without a valid blockchain record ID."
        )

    fingerprint_bytes32 = bytes.fromhex(
        expected_fingerprint_hex
    )

    verified = contract.functions.verify(
        int(record_id),
        fingerprint_bytes32
    ).call()

    return bool(verified)