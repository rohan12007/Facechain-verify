import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from pipeline import run  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Face scan -> social search -> blockchain verification pipeline"
    )

    parser.add_argument(
        "--image",
        required=True,
        help="Path to the face scan image"
    )

    parser.add_argument(
        "--mode",
        choices=["tx", "contract"],
        default="contract",
        help="'tx' = no smart contract, hash lives in tx data. "
             "'contract' = calls ProofRegistry.sol (default)."
    )

    parser.add_argument(
        "--network",
        choices=["local", "sepolia", "amoy"],
        default="local"
    )

    args = parser.parse_args()

    print(json.dumps(
        run(args.image, args.mode, args.network),
        indent=2
    ))