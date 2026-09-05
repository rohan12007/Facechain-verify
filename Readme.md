## Architecture Overview

┌─────────────────┐     ┌─────────────────────────────────────────────────────┐
│   Frontend      │     │                   Flask Backend                    │
│ (HTML/JS)       │     │                                                     │
│                 │     │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  - Upload form  │────▶│  │ /upload     │─▶│ Face Detection│─▶│ Reverse    │ │
│  (or camera)    │     │  │ (POST)      │  │ & Encoding    │  │ Image      │ │
│                 │     │  └─────────────┘  └──────────────┘  │ Search     │ │
│                 │     │                                    └────────────┘ │
│                 │     │                                          │        │
│                 │     │                                          ▼        │
│                 │     │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│                 │     │  │ /verify     │◀─│ Blockchain   │◀─│ Extract    │ │
│                 │     │  │ (GET)       │  │ Upload       │  │ Post Data  │ │
│                 │     │  └─────────────┘  └──────────────┘  └────────────┘ │
└─────────────────┘     └─────────────────────────────────────────────────────┘




## Folder Structure 
Facechain-verify/
├── Backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── routes.py          # Flask endpoints
│   │   ├── face_utils.py      # face detection & encoding
│   │   ├── search_utils.py    # reverse image search
│   │   ├── blockchain_utils.py# web3 interactions
│   │   ├── config.py          # API keys, contract address, etc.
│   │   └── templates/
│   │       └── index.html     # simple upload frontend
│   ├── main.py                # entry point
│   ├── requirements.txt
│   ├── .env                   # environment variables (not in repo)
│   └── venv/                  # virtual environment
└── README.md