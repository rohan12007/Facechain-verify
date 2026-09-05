# Face Scan → Social Match → Blockchain Verification

An end-to-end pipeline: take a face photo → find a matching public social
media post via reverse image search → hash the result and write it to a
blockchain so it can be independently re-verified later.

```
 face photo  ──▶  face detection    ──▶  reverse image      ──▶  hash the
 (selfie/scan)     + embedding           search (find a           match +
                    (DeepFace)            public social post)      upload to
                                                                     chain
                                                                        │
                                                              ┌─────────┘
                                                              ▼
                                                   re-fetch record on-chain
                                                   and confirm hashes match
```

## What this is (and isn't)

This was built for a "genuine search, not hardcoded" pipeline assignment.
To keep it ethical, the design assumption throughout is: **you run this on
your own face and your own existing public posts** (or a teammate's, with
their explicit sign-off), not on photos of strangers. The reverse-image
step is a real, general-purpose search (Google's Web Detection API) — it's
just pointed only at consenting test subjects. See **Ethics & limitations**
below for why that boundary matters and isn't just a formality.

## Pipeline stages

1. **Face detection + encoding** (`src/face_module.py`) — [DeepFace](https://github.com/serengil/deepface)
   detects the face and produces a 512-d embedding (Facenet512 model,
   RetinaFace detector). Also exposes a cosine-distance comparator in case
   you want to double-check the search result actually contains the same
   face (see "Ideas to extend" below).
2. **Reverse image / social search** (`src/social_search.py`) — calls
   Google Cloud Vision's [Web Detection](https://cloud.google.com/vision/docs/detecting-web)
   feature, which returns pages and images across the web that match or
   closely resemble the input photo. Results are filtered down to known
   social domains (Instagram, X/Twitter, Facebook, LinkedIn, Reddit,
   TikTok, Threads).
3. **Blockchain upload + verification** (`src/blockchain_verify.py`) —
   SHA-256-hashes the image bytes + matched URL into a single fingerprint,
   writes it on-chain, then reads it back and compares. Two modes:
   - `--mode contract` (default): calls `submitProof()` on the
     `ProofRegistry` smart contract (`blockchain/contracts/ProofRegistry.sol`),
     which stores the fingerprint, URL, timestamp, and submitter address as
     a queryable record + emits an event.
   - `--mode tx`: no contract needed — the fingerprint is written directly
     into a self-send transaction's `data` field. Faster to set up if
     you're short on time.

## Which blockchain

Any EVM-compatible chain works with this code unchanged — just point the
RPC URL at it. Two networks are pre-wired:

- **Local Hardhat network** (default, `--network local`) — a fully
  simulated chain running on your own machine via `npx hardhat node`. No
  faucet, no real funds, no flaky public RPC — the most reliable option for
  a demo/recording. This is the recommended path if you're tight on time.
- **Ethereum Sepolia testnet** (`--network sepolia`) — a real public
  testnet, useful if you want the recording to show a transaction on a
  real block explorer (sepolia.etherscan.io). Needs a free RPC URL
  (Infura/Alchemy) and free test ETH from a Sepolia faucet.
- Polygon's **Amoy** testnet is also wired up (`--network amoy`) as a
  lower-fee alternative to Sepolia (Polygon's older Mumbai testnet was
  deprecated in 2024 — Amoy is its replacement).

## Setup

Requires **Python 3.10+** and **Node.js 18+** (for the Hardhat/contract
side, only needed if you use `--mode contract`).

```bash
# 1. Python side
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Node/Hardhat side (skip if you're only using --mode tx)
cd blockchain
npm install
cd ..

# 3. Configure secrets
cp .env.example .env
# then edit .env — see below for what each value needs
```

### Google Cloud Vision credentials

1. Create a GCP project (free tier is enough) and enable the **Cloud
   Vision API**.
2. Create a service account, grant it the "Cloud Vision API User" role,
   and download its JSON key.
3. Save it as `gcp-service-account.json` in the project root (already
   git-ignored) and make sure `.env`'s `GOOGLE_APPLICATION_CREDENTIALS`
   points at it.

### Blockchain account

Generate a **throwaway** wallet for testing (e.g. `npx hardhat node` prints
10 pre-funded local accounts with private keys on startup — just copy one
of those into `.env`'s `PRIVATE_KEY` for local mode). Never reuse a real
wallet's key here.

## Running it

**Option A — local simulated chain (recommended, fastest):**

```bash
# Terminal 1: start a local chain
cd blockchain && npx hardhat node

# Terminal 2: deploy the contract to it
cd blockchain && npm run deploy:local
# copy the printed CONTRACT_ADDRESS into your .env

# Terminal 3: run the pipeline
python main.py --image tests/sample_data/my_photo.jpg --mode contract --network local
```

**Option B — no contract at all (fastest possible setup):**

```bash
cd blockchain && npx hardhat node          # still need a chain to send a tx to
python main.py --image tests/sample_data/my_photo.jpg --mode tx --network local
```

**Option C — real testnet (Sepolia), for a "real blockchain" demo:**

```bash
cd blockchain && npm run deploy:sepolia   # after filling in SEPOLIA_RPC_URL + PRIVATE_KEY
python main.py --image tests/sample_data/my_photo.jpg --mode contract --network sepolia
```

Each run prints the detected embedding size, the matched social post URL,
the fingerprint hash, the transaction hash (and record id, in contract
mode), and finally `VERIFIED: True/False` after independently re-deriving
the fingerprint and comparing it against what's stored on-chain.

Run the offline unit tests with:

```bash
pytest tests/
```

## Screen recording checklist

For the submission recording, show, in one continuous take:
1. The input photo.
2. The console output of stage 1–2 (face detected → matched URL found) —
   pause on the matched URL so it's clearly a real, live post.
3. The upload step's printed tx hash, and that tx/record looked up on a
   block explorer (Etherscan for Sepolia) or via `getRecord()` for local.
4. The final `VERIFIED: True` line.

## Ethics & limitations (known limitations, as required by the task)

- **Consent boundary.** The search step is a genuine, general-purpose
  reverse-image search — it isn't hardcoded to any one result — but it's
  designed and tested only against the operator's own face/posts or a
  consenting volunteer's. Pointed at an arbitrary stranger's photo, this
  same technique is the basis of controversial "find this person" face-search
  services that have drawn significant regulatory and legal scrutiny for
  enabling stalking/harassment. This repo does not include any code to
  scale that up (no batch processing of unknown faces, no face database).
- **Search coverage is limited.** Google's Web Detection only surfaces
  content it has crawled and indexed; a private account, a very recent
  post, or a platform that blocks indexing (e.g. many Instagram posts)
  may simply not show up, even for a genuine match.
- **Face-matching accuracy.** DeepFace/Facenet embeddings can produce
  false positives/negatives, especially across very different lighting,
  age, or image quality — `is_same_person()` is provided as an optional
  extra check but isn't relied on to gate the pipeline by default.
- **Not legal/forensic-grade proof.** Writing a hash on-chain proves the
  hash existed at that block time and hasn't changed since — it does
  **not** prove who is in the photo, that the matched post is genuinely
  the same person, or anything about chain-of-custody before the upload.
- **Testnet/local chain only in this default config** — a mainnet
  deployment would need real funds and additional security review
  (access control on `submitProof`, rate limiting, etc.) before any
  production use.

## Ideas to extend

- Call `is_same_person()` on a downloaded thumbnail of the matched image
  vs. the input embedding, and only proceed if it actually matches — turns
  "a page with a visually similar image" into "a page with *this* face".
- Add IPFS pinning of the matched image/metadata and store the IPFS CID
  on-chain instead of (or alongside) the raw hash.
- Swap Google Vision for TinEye or SerpApi's reverse-image endpoint to
  compare index coverage.
