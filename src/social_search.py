"""
Reverse image / web search step.

Uses Google Cloud Vision's Web Detection feature: a general-purpose "find
this image elsewhere on the web" API (also used for things like reverse
image lookup, copyright / plagiarism checks) -- not a dedicated face-search
product. Docs: https://cloud.google.com/vision/docs/detecting-web

READ THIS BEFORE YOU RUN IT:
Only run this against photos of yourself, or of people who have explicitly
agreed to be part of your test (e.g. teammates who volunteered their own
photo + know which of their own posts they expect it to find). Do not point
this at photos of strangers you found online. See the README's
"Ethics & limitations" section for why.
"""

from typing import List, Dict, Optional

from google.cloud import vision

SOCIAL_DOMAINS = [
    "twitter.com", "x.com", "instagram.com", "facebook.com",
    "linkedin.com", "reddit.com", "tiktok.com", "threads.net",
]


def reverse_image_search(image_path: str) -> List[Dict]:
    """Runs Google Cloud Vision web detection on the given image and returns
    a flat list of {url, match_type, page_title?} dicts."""
    client = vision.ImageAnnotatorClient()

    with open(image_path, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)
    response = client.web_detection(image=image)

    if response.error.message:
        raise RuntimeError(response.error.message)

    web = response.web_detection
    matches: List[Dict] = []

    for page in web.pages_with_matching_images:
        matches.append({
            "url": page.url,
            "match_type": "page_with_matching_image",
            "page_title": getattr(page, "page_title", None),
        })

    for img in web.full_matching_images:
        matches.append({"url": img.url, "match_type": "full_image_match"})

    for img in web.partial_matching_images:
        matches.append({"url": img.url, "match_type": "partial_image_match"})

    return matches


def filter_social_matches(matches: List[Dict], domains: Optional[List[str]] = None) -> List[Dict]:
    """Keep only results whose URL is on a known social media domain."""
    domains = domains or SOCIAL_DOMAINS
    return [m for m in matches if any(d in m["url"] for d in domains)]
