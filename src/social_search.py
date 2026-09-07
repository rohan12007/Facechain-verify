from __future__ import annotations

import os
import re
from typing import Dict, List
from urllib.parse import urlparse

import cv2
from deepface import DeepFace
from playwright.sync_api import sync_playwright


SOCIAL_DOMAINS = [
    "instagram.com",
    "facebook.com",
    "linkedin.com",
    "reddit.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "threads.net",
]


def _hostname(url: str) -> str:
    try:
        hostname = (urlparse(url).hostname or "").lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        return hostname

    except Exception:
        return ""


def _is_social_url(url: str) -> bool:
    hostname = _hostname(url)

    return any(
        hostname == domain
        or hostname.endswith("." + domain)
        for domain in SOCIAL_DOMAINS
    )


def create_face_crop(image_path: str) -> str:
    """
    Detect the largest face using DeepFace/OpenCV and create
    a face-focused image for Google Lens.

    The original image is NOT modified.
    """

    print("      -> detecting face with DeepFace...")

    faces = DeepFace.extract_faces(
        img_path=image_path,
        detector_backend="opencv",
        enforce_detection=True,
        align=True,
    )

    if not faces:
        raise RuntimeError(
            "No face was detected in the input image."
        )

    # Choose the largest detected face
    best_face = max(
        faces,
        key=lambda item: (
            item["facial_area"]["w"]
            * item["facial_area"]["h"]
        ),
    )

    area = best_face["facial_area"]

    x = int(area["x"])
    y = int(area["y"])
    w = int(area["w"])
    h = int(area["h"])

    print(
        f"      -> face detected: "
        f"x={x}, y={y}, w={w}, h={h}"
    )

    image = cv2.imread(image_path)

    if image is None:
        raise RuntimeError(
            f"Could not read image: {image_path}"
        )

    image_h, image_w = image.shape[:2]

    # Add padding around the face.
    # This gives Lens some context while keeping the face dominant.
    padding_x = int(w * 0.55)
    padding_y = int(h * 0.65)

    x1 = max(0, x - padding_x)
    y1 = max(0, y - padding_y)

    x2 = min(image_w, x + w + padding_x)
    y2 = min(image_h, y + h + padding_y)

    face_crop = image[y1:y2, x1:x2]

    if face_crop.size == 0:
        raise RuntimeError(
            "Face crop was empty."
        )

    crop_path = os.path.join(
        os.path.dirname(os.path.abspath(image_path)),
        "face_lens_crop.jpg",
    )

    success = cv2.imwrite(
        crop_path,
        face_crop,
        [
            cv2.IMWRITE_JPEG_QUALITY,
            95,
        ],
    )

    if not success:
        raise RuntimeError(
            "Failed to save face crop."
        )

    print(
        f"      -> face crop created: {crop_path}"
    )

    return crop_path


def _extract_social_urls_from_html(
    html: str,
) -> List[Dict]:
    """
    Extract actual social-media URLs from the rendered
    Google Lens results page.
    """

    results = []
    seen = set()

    url_pattern = re.compile(
        r'https://(?:www\.)?'
        r'(?:instagram\.com|facebook\.com|linkedin\.com|'
        r'reddit\.com|twitter\.com|x\.com|tiktok\.com|'
        r'threads\.net)'
        r'(?:/[A-Za-z0-9._~:/?#\[\]@!$&\'()*+,;=%-]*)?',
        re.IGNORECASE,
    )

    matches = url_pattern.findall(html)

    for url in matches:

        url = (
            url.replace("\\u0026", "&")
            .replace("\\u003d", "=")
            .replace("\\/", "/")
            .replace("&amp;", "&")
        )

        url = (
            url.split("&quot;", 1)[0]
            .split("\\", 1)[0]
            .split('"', 1)[0]
            .split("'", 1)[0]
            .rstrip("/")
        )

        if not _is_social_url(url):
            continue

        path = urlparse(url).path.lower()

        if path in ("", "/"):
            continue

        if url in seen:
            continue

        seen.add(url)

        results.append(
            {
                "url": url,
                "match_type": "google_lens_result",
                "page_title": "",
            }
        )

    return results


def _extract_social_urls_from_links(
    page,
) -> List[Dict]:
    """
    Extract social-media URLs from clickable links
    on the Google Lens results page.
    """

    results = []
    seen = set()

    links = page.locator("a")

    for i in range(links.count()):

        try:
            link = links.nth(i)

            href = link.get_attribute("href")

            if not href:
                continue

            href = href.strip()

            if not href.startswith(
                ("http://", "https://")
            ):
                continue

            if not _is_social_url(href):
                continue

            path = urlparse(href).path.lower()

            if path in ("", "/"):
                continue

            if href in seen:
                continue

            seen.add(href)

            try:
                title = link.inner_text(
                    timeout=1000
                ).strip()
            except Exception:
                title = ""

            results.append(
                {
                    "url": href,
                    "match_type": "google_lens_link",
                    "page_title": title,
                }
            )

        except Exception:
            continue

    return results


def reverse_image_search(
    image_path: str,
) -> List[Dict]:
    """
    Genuine Google Lens reverse-image search.

    First creates a face-focused crop using DeepFace.
    The user then uploads that crop to Google Lens manually.

    No social-media URL is hardcoded.
    """

    # --------------------------------------------------
    # STEP 1: Detect face and create face-focused image
    # --------------------------------------------------

    lens_image = create_face_crop(image_path)

    print()
    print(
        "=" * 65
    )
    print(
        "FACE IMAGE READY FOR GOOGLE LENS"
    )
    print(
        "=" * 65
    )
    print()
    print(
        f"Upload this image to Google Lens:"
    )
    print()
    print(
        f"   {lens_image}"
    )
    print()
    print(
        "The crop contains the detected face,"
    )
    print(
        "so Lens should not select the clothing/background."
    )
    print()
    print(
        "=" * 65
    )
    print()

    results = []

    with sync_playwright() as p:

        print(
            "      -> opening visible Chrome..."
        )

        browser = p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--start-maximized",
            ],
        )

        context = browser.new_context(
            viewport={
                "width": 1440,
                "height": 1000,
            },
            locale="en-US",
        )

        page = context.new_page()

        try:

            print(
                "      -> opening Google..."
            )

            page.goto(
                "https://www.google.com/",
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(3000)

            print()
            print(
                "=" * 65
            )
            print(
                "MANUAL GOOGLE LENS STEP"
            )
            print(
                "=" * 65
            )
            print()
            print(
                "1. Click Google Lens / Search by image."
            )
            print(
                "2. Select 'Upload a file'."
            )
            print()
            print(
                "3. Upload:"
            )
            print()
            print(
                f"   {lens_image}"
            )
            print()
            print(
                "4. Complete Google's verification if shown."
            )
            print()
            print(
                "5. Wait until Lens results are visible."
            )
            print()
            print(
                "=" * 65
            )
            print()

            input(
                "Press ENTER after Lens results are visible: "
            )

            page.wait_for_timeout(3000)

            print()
            print(
                f"      -> result page: {page.url}"
            )

            print(
                "      -> scrolling Lens results..."
            )

            for _ in range(5):

                page.mouse.wheel(
                    0,
                    1000,
                )

                page.wait_for_timeout(1200)

            print(
                "      -> extracting social URLs "
                "from Lens page data..."
            )

            html = page.content()

            html_results = (
                _extract_social_urls_from_html(
                    html
                )
            )

            print(
                "      -> checking clickable links..."
            )

            link_results = (
                _extract_social_urls_from_links(
                    page
                )
            )

            combined = []
            seen = set()

            for item in (
                html_results + link_results
            ):

                url = item["url"]

                if url in seen:
                    continue

                seen.add(url)

                combined.append(item)

            results = combined

            print()
            print(
                f"      -> discovered "
                f"{len(results)} social-media "
                f"result(s)"
            )

            for index, result in enumerate(
                results,
                start=1,
            ):

                print(
                    f"         [{index}] "
                    f"{result['url']}"
                )

            if not results:

                page.screenshot(
                    path="google_lens_debug.png",
                    full_page=True,
                )

                with open(
                    "google_lens_debug.html",
                    "w",
                    encoding="utf-8",
                ) as f:

                    f.write(
                        page.content()
                    )

                print()
                print(
                    "      -> no social results found"
                )

                print(
                    "      -> debug files saved:"
                )

                print(
                    "         google_lens_debug.png"
                )

                print(
                    "         google_lens_debug.html"
                )

        finally:

            browser.close()

    return results


def filter_social_matches(
    matches: List[Dict],
    domains: List[str] | None = None,
) -> List[Dict]:

    domains = domains or SOCIAL_DOMAINS

    normalized_domains = []

    for domain in domains:

        domain = domain.lower().strip()

        if domain.startswith("www."):
            domain = domain[4:]

        normalized_domains.append(
            domain
        )

    results = []

    for match in matches:

        url = match.get(
            "url",
            "",
        )

        hostname = _hostname(url)

        if any(
            hostname == domain
            or hostname.endswith("." + domain)
            for domain in normalized_domains
        ):

            path = urlparse(url).path.lower()

            if path in ("", "/"):
                continue

            results.append(match)

    return results


def search_social_media(
    image_path: str,
) -> List[Dict]:

    results = reverse_image_search(
        image_path
    )

    return filter_social_matches(
        results
    )