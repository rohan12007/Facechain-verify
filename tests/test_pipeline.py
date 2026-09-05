"""
Minimal sanity tests for the pure/offline parts of the pipeline. These do
NOT require GCP credentials, a face model download, or a live chain -- they
just check that the plumbing (hashing, filtering) behaves as expected.

Run with:  pytest tests/
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np  # noqa: E402
from face_module import cosine_distance  # noqa: E402
from social_search import filter_social_matches  # noqa: E402
from blockchain_verify import compute_fingerprint  # noqa: E402


def test_cosine_distance_identical_vectors_is_zero():
    v = np.array([1.0, 2.0, 3.0])
    assert cosine_distance(v, v) < 1e-9


def test_cosine_distance_orthogonal_vectors_is_one():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert abs(cosine_distance(a, b) - 1.0) < 1e-9


def test_filter_social_matches_keeps_only_known_domains():
    matches = [
        {"url": "https://instagram.com/p/abc123", "match_type": "full_image_match"},
        {"url": "https://randomblog.example.com/post", "match_type": "full_image_match"},
    ]
    filtered = filter_social_matches(matches)
    assert len(filtered) == 1
    assert "instagram.com" in filtered[0]["url"]


def test_fingerprint_is_deterministic(tmp_path):
    img = tmp_path / "fake.jpg"
    img.write_bytes(b"not a real image, just bytes for hashing purposes")

    fp1 = compute_fingerprint(str(img), "https://example.com/post/1")
    fp2 = compute_fingerprint(str(img), "https://example.com/post/1")
    assert fp1 == fp2
    assert len(fp1) == 64  # sha256 hex digest length


def test_fingerprint_changes_if_url_changes(tmp_path):
    img = tmp_path / "fake.jpg"
    img.write_bytes(b"not a real image, just bytes for hashing purposes")

    fp1 = compute_fingerprint(str(img), "https://example.com/post/1")
    fp2 = compute_fingerprint(str(img), "https://example.com/post/2")
    assert fp1 != fp2
