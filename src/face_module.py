"""
Face detection + embedding extraction.

Uses DeepFace (https://github.com/serengil/deepface), which bundles several
detector backends (opencv, retinaface, mtcnn, ...) and recognition models
(Facenet512, ArcFace, VGG-Face, ...) behind one simple API. We default to
Facenet512 + retinaface, a good accuracy/speed tradeoff for a laptop demo.
"""

from typing import Tuple

import numpy as np
from deepface import DeepFace

DEFAULT_MODEL = "Facenet512"
DEFAULT_DETECTOR = "retinaface"

# Empirically reasonable cosine-distance cutoff for Facenet512 (DeepFace's
# own verification thresholds table uses ~0.30 for this model). Tune this
# against your own test photos before you trust it for anything real.
DEFAULT_MATCH_THRESHOLD = 0.30


def get_face_embedding(
    image_path: str,
    model_name: str = DEFAULT_MODEL,
    detector_backend: str = DEFAULT_DETECTOR,
) -> np.ndarray:
    """
    Detect the (first/largest) face in `image_path` and return its embedding
    vector. Raises ValueError if no face is detected.
    """
    try:
        reps = DeepFace.represent(
            img_path=image_path,
            model_name=model_name,
            detector_backend=detector_backend,
            enforce_detection=True,
        )
    except Exception as e:  # DeepFace raises plain Exception on "no face"
        raise ValueError(f"No face detected in {image_path}: {e}") from e

    if not reps:
        raise ValueError(f"No face detected in {image_path}")

    return np.array(reps[0]["embedding"])


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return 1.0 - float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def is_same_person(
    embedding_a: np.ndarray,
    embedding_b: np.ndarray,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> Tuple[bool, float]:
    """Returns (is_match, cosine_distance)."""
    distance = cosine_distance(embedding_a, embedding_b)
    return distance < threshold, distance
