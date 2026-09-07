# Face Scan → Social Match → Blockchain Verification

An end-to-end proof-of-concept pipeline for the Hacker House Goa 2026 Task 3:

**Face scan input → face detection/embedding → face-focused reverse image search → public social-media result → blockchain fingerprint → on-chain verification**

The project demonstrates a genuine search step rather than using a hardcoded or manually supplied social-media URL.

---

## What this project does

Given a test face image, the pipeline:

1. Detects and encodes the face using **DeepFace / FaceNet512**.
2. Detects the face again and creates a **face-focused crop** for reverse-image search.
3. Opens **Google Lens** in a visible browser and lets the operator upload the generated face crop.
4. Extracts social-media URLs discovered by the live Lens results.
5. Selects a discovered social-media result dynamically.
6. Generates a SHA-256 fingerprint from the input image and matched URL.
7. Stores the fingerprint and matched URL in a local **Hardhat / ProofRegistry** blockchain.
8. Reads the record back from the blockchain and independently verifies the fingerprint.
9. Prints `VERIFIED: True` when the on-chain fingerprint matches.

### Pipeline

```text
                    ┌─────────────────────┐
                    │   Input face image  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ DeepFace face       │
                    │ detection + 512-d   │
                    │ embedding           │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Face-focused crop   │
                    │ face_lens_crop.jpg  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Google Lens         │
                    │ reverse-image search│
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Social-media result │
                    │ discovered live     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ SHA-256 fingerprint │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ ProofRegistry       │
                    │ local blockchain    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Re-verify on-chain  │
                    │ VERIFIED: True      │
                    └─────────────────────┘
```

---

## Important usage boundary

This proof of concept should be used only with **your own image/public posts** or with a teammate/volunteer who has explicitly agreed to the test.

The reverse-image search is a genuine general-purpose search. The repository does **not** hardcode a particular social-media result or provide a database of unknown people.

The system is a technical demonstration, not an identity/forensic system.

---

## Project structure

```text
Facechain-verify/
│
├── main.py
├── requirements.txt
├── .env.example
├── README.md
│
├── src/
│   ├── face_module.py
│   ├── social_search.py
│   ├── blockchain_verify.py
│   └── pipeline.py
│
├── tests/
│   ├── sample_data/
│   │   └── instagram_test.jpeg
│   └── ...
│
└── blockchain/
    ├── contracts/
    │   └── ProofRegistry.sol
    ├── scripts/
    │   └── deploy.js
    ├── hardhat.config.js
    └── package.json
```

---

## Technology stack

### AI / Computer Vision

- Python 3.11
- DeepFace
- FaceNet512
- OpenCV
- TensorFlow / tf-keras

### Reverse image search

- Google Lens
- Playwright
- Chromium

Google Lens is used through a **visible browser**. The operator uploads the generated face-focused crop manually and completes any Google verification normally.

### Blockchain

- Solidity
- Hardhat
- Web3.py
- Local EVM blockchain
- `ProofRegistry.sol`

### Hashing

- SHA-256

---

## Pipeline stages

### 1. Face detection and embedding

`src/face_module.py`

DeepFace detects the face and generates a 512-dimensional FaceNet512 embedding.

Example output:

```text
[1/4] Detecting face in tests/sample_data/instagram_test.jpeg ...
      -> got a 512-dim face embedding
```

The embedding is useful for representing the detected face numerically.

---

### 2. Face-focused reverse image search

`src/social_search.py`

Before opening Google Lens, the program detects the face and creates a focused crop.

Example:

```text
-> detecting face with DeepFace...
-> face detected: x=200, y=80, w=274, h=274
-> face crop created:
   /home/nova/Facechain-verify/tests/sample_data/face_lens_crop.jpg
```

The original image is not modified.

The crop is then uploaded to Google Lens manually.

```text
Original image
      ↓
DeepFace detects face
      ↓
Face crop
      ↓
Google Lens
      ↓
Social-media candidates
```

The search code does not contain a hardcoded social-media URL.

Supported social domains include:

- Instagram
- Facebook
- X / Twitter
- LinkedIn
- Reddit
- TikTok
- Threads

---

## Google Lens step

The browser is intentionally visible because Google may require human verification.

When the program displays:

```text
MANUAL GOOGLE LENS STEP
```

do the following:

1. Click Google Lens / Search by image.
2. Select **Upload a file**.
3. Upload the generated:

```text
face_lens_crop.jpg
```

4. Complete Google's verification if requested.
5. Wait until the Lens results are visible.
6. Return to the terminal and press **ENTER**.

The program then extracts social-media URLs from the rendered Lens results.

Example:

```text
-> discovered 24 social-media result(s)
-> collected 24 candidate web result(s)
-> found 24 social-media candidate(s)
-> discovered social match: https://www.instagram.com/...
```

The exact result will vary because Google Lens results are dynamic.

---

## 3. Blockchain upload

`src/blockchain_verify.py`

The pipeline creates a SHA-256 fingerprint from:

```text
image bytes + matched social-media URL
```

Example:

```text
-> fingerprint:
9150367715d1d8dba8706c47aa8dad0ef00fe20751563b1f2cbfaa59807a1d51
```

The default blockchain mode uses the `ProofRegistry` smart contract.

The contract stores:

- fingerprint
- matched URL
- timestamp
- submitting address

---

## 4. Blockchain verification

After the transaction is confirmed, the pipeline retrieves the stored record and compares the stored fingerprint with the locally generated fingerprint.

Example:

```text
-> transaction confirmed: 0x...
-> record id from event: 0
-> on-chain record confirmed

[4/4] Re-verifying against the on-chain record ...
      -> VERIFIED: True
```

Final output:

```json
{
  "matched_url": "https://www.instagram.com/...",
  "fingerprint": "...",
  "tx_hash": "0x...",
  "record_id": 0,
  "verified": true
}
```

---

# Setup

## Requirements

Recommended environment:

- Python **3.11**
- Node.js 18+
- npm
- Chromium
- Hardhat

Python 3.11 is recommended because the DeepFace / TensorFlow stack can have compatibility issues on newer Python versions.

---

## 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Facechain-verify
```

---

## 2. Create the Python virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

If Playwright's browser has not been installed:

```bash
playwright install chromium
```

---

## 3. Install the blockchain dependencies

```bash
cd blockchain
npm install
cd ..
```

---

## 4. Configure `.env`

Create the environment file:

```bash
cp .env.example .env
```

For local Hardhat testing, configure the required blockchain values in `.env`.

Example structure:

```env
PRIVATE_KEY=YOUR_LOCAL_HARDHAT_PRIVATE_KEY
CONTRACT_ADDRESS=YOUR_DEPLOYED_PROOF_REGISTRY_ADDRESS
```

### Security

Never commit:

```text
.env
PRIVATE_KEY
service-account JSON files
real wallet credentials
```

Use only a throwaway Hardhat account for local testing.

---

# Running the project

## Recommended local blockchain workflow

Because the demo uses a local Hardhat blockchain, use three terminals.

### Terminal 1 — Start Hardhat

```bash
cd ~/Facechain-verify/blockchain
npx hardhat node
```

Keep this terminal running.

---

### Terminal 2 — Deploy the contract

```bash
cd ~/Facechain-verify/blockchain
npx hardhat run scripts/deploy.js --network localhost
```

The deployment prints a new `CONTRACT_ADDRESS`.

Update `.env` in the project root with that address:

```env
CONTRACT_ADDRESS=<address printed by deployment>
```

### Important

The local Hardhat chain is reset when `npx hardhat node` is stopped.

Therefore, after restarting the Hardhat node:

1. Start the node.
2. Deploy `ProofRegistry` again.
3. Update `CONTRACT_ADDRESS`.
4. Run the Python pipeline.

Do not restart the Hardhat node while the demo is running.

---

### Terminal 3 — Run the pipeline

```bash
cd ~/Facechain-verify
source venv/bin/activate

python main.py \
  --image tests/sample_data/instagram_test.jpeg \
  --mode contract \
  --network local
```

---

# Example successful run

A successful run should contain output similar to:

```text
[1/4] Detecting face ...
      -> got a 512-dim face embedding

[2/4] Running genuine reverse image search ...
      -> detecting face with DeepFace...
      -> face detected: x=200, y=80, w=274, h=274
      -> face crop created: .../face_lens_crop.jpg

      -> discovered 24 social-media result(s)
      -> discovered social match: https://www.instagram.com/...

[3/4] Hashing + uploading to blockchain ...
      -> fingerprint: ...
      -> transaction confirmed: 0x...
      -> record id from event: 0
      -> on-chain record confirmed

[4/4] Re-verifying against the on-chain record ...
      -> VERIFIED: True
```

The exact Lens result, number of candidates, fingerprint, transaction hash, and record ID can change between runs.

---

# Command-line options

```bash
python main.py --image <IMAGE_PATH>
```

### Contract mode

Default and recommended for the Task 3 demonstration:

```bash
python main.py \
  --image tests/sample_data/instagram_test.jpeg \
  --mode contract \
  --network local
```

### Transaction-data mode

An alternative blockchain demonstration that does not use `ProofRegistry`:

```bash
python main.py \
  --image tests/sample_data/instagram_test.jpeg \
  --mode tx \
  --network local
```

The contract mode is preferred because it demonstrates a queryable blockchain record and explicit re-verification.

---

# Smart contract

`blockchain/contracts/ProofRegistry.sol`

The contract contains:

```solidity
struct Record {
    bytes32 fingerprint;
    string matchedUrl;
    uint256 timestamp;
    address submitter;
}
```

The main functions are:

```text
submitProof()
getRecord()
verify()
totalRecords()
```

`submitProof()` creates a record and emits a `ProofSubmitted` event.

`getRecord()` retrieves the stored record.

`verify()` compares a supplied fingerprint with the stored fingerprint.

---

# Testing

Run the available tests with:

```bash
pytest tests/
```

---

# Screen-recording checklist

For the Hacker House Goa Task 3 demonstration, show the complete flow in one continuous recording.

### 1. Face input

Show the input test image.

### 2. Face detection

Show:

```text
[1/4] Detecting face ...
-> got a 512-dim face embedding
```

### 3. Face crop

Show:

```text
-> face detected: ...
-> face crop created: .../face_lens_crop.jpg
```

### 4. Genuine reverse-image search

Show the Google Lens upload and the resulting search page.

The search must be performed live rather than using a hardcoded URL.

### 5. Social-media match

Show that Lens produced social-media results and that the program discovered one dynamically.

### 6. Blockchain upload

Show:

```text
-> fingerprint: ...
-> transaction confirmed: 0x...
-> on-chain record confirmed
```

### 7. Final verification

End with:

```text
-> VERIFIED: True
```

This demonstrates:

```text
Face scan
   ↓
Reverse image search
   ↓
Social post discovered
   ↓
Blockchain upload
   ↓
Blockchain re-verification
```

---

# Known limitations

### Google Lens results are dynamic

Search results can differ between runs. A social-media result may appear in one search and not another.

### Search indexing

Private, deleted, very recent, or poorly indexed posts may not appear in reverse-image results.

### Manual browser step

Google Lens may require human interaction or verification. The project intentionally does not attempt to bypass these checks.

### Face recognition accuracy

DeepFace embeddings can produce false positives or false negatives depending on image quality, lighting, pose, and other factors.

### Blockchain scope

The default setup uses a local Hardhat blockchain for demonstration. It is not a production blockchain deployment.

### Hash verification is not identity proof

A blockchain fingerprint proves that a particular fingerprint was recorded on-chain. It does **not** prove the identity of the person in an image or establish forensic chain of custody.

---

# Ethics

This project is intended as a technical demonstration of:

- face detection
- reverse-image search
- social-media result discovery
- cryptographic fingerprinting
- blockchain verification

It should only be tested with images belonging to the operator or consenting participants.

The repository does not provide a database of unknown people, batch processing of arbitrary faces, or a mechanism for bypassing platform security or verification systems.

---

# Future improvements

Possible extensions include:

- Compare the detected face embedding with a thumbnail from the discovered result before accepting it.
- Add multiple-result ranking instead of selecting the first social result.
- Store structured metadata alongside the fingerprint.
- Store an IPFS CID alongside the on-chain fingerprint.
- Add a small dashboard for visualizing blockchain records.
- Add additional reverse-image providers for broader search coverage.
- Add automated tests for URL extraction and fingerprint verification.

---

# Task 3 requirement mapping

| Task requirement | Implementation |
|---|---|
| Face identification | DeepFace / FaceNet512 |
| Detect and encode face | `src/face_module.py` |
| Genuine web/social search | Google Lens via Playwright |
| No hardcoded result | Social URL is extracted from live Lens results |
| Social-media matching | Instagram, Facebook, X/Twitter, LinkedIn, Reddit, TikTok, Threads |
| Blockchain upload | `ProofRegistry.sol` |
| Fingerprint | SHA-256 |
| Blockchain verification | `getRecord()` + fingerprint comparison |
| Demonstration | Screen recording of complete pipeline |
| Repository | GitHub + this README |

---

## Final result

The project demonstrates the required end-to-end workflow:

```text
Face Scan
    ↓
DeepFace Face Detection + Embedding
    ↓
Face-Focused Crop
    ↓
Google Lens Reverse Image Search
    ↓
Social-Media Result Discovered
    ↓
SHA-256 Fingerprint
    ↓
ProofRegistry Blockchain Record
    ↓
On-Chain Re-Verification
    ↓
VERIFIED: True
```

