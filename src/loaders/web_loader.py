"""
web_loader.py
--------------
Fetches web pages / blog posts / docs pages from data/urls.txt,
strips out navbars/ads/footers, converts to clean Markdown, and
saves each one to data/raw/web_cache/<slug>.md.
"""

import os
import re
import hashlib
import trafilatura
from src import config


def _slugify(url: str) -> str:
    clean = re.sub(r"https?://", "", url)
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", clean).strip("_")[:80]
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{clean}_{url_hash}"


def _clean_markdown(text: str) -> str:
    text = re.sub(r"&nbsp;|&amp;|&quot;", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    boilerplate_patterns = [
        r"(?i)^.*subscribe to our newsletter.*$",
        r"(?i)^.*accept cookies.*$",
        r"(?i)^.*all rights reserved.*$",
    ]
    lines = text.split("\n")
    filtered = [ln for ln in lines if not any(re.match(p, ln) for p in boilerplate_patterns)]
    return "\n".join(filtered).strip()


def fetch_and_convert(url: str):
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        print(f"[web_loader] FAILED to download: {url}")
        return None

    extracted = trafilatura.extract(
        downloaded,
        output_format="markdown",
        include_links=False,
        include_images=False,
        include_tables=True,
        favor_precision=True,
    )
    if not extracted:
        print(f"[web_loader] FAILED to extract content: {url}")
        return None

    cleaned = _clean_markdown(extracted)

    os.makedirs(config.WEB_CACHE_DIR, exist_ok=True)
    filename = _slugify(url) + ".md"
    filepath = os.path.join(config.WEB_CACHE_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"<!-- source_url: {url} -->\n\n{cleaned}")

    print(f"[web_loader] Saved: {url} -> {filepath}")
    return filepath


def ingest_urls_from_file(urls_file: str = None):
    urls_file = urls_file or config.URLS_FILE
    if not os.path.exists(urls_file):
        print(f"[web_loader] No urls file found at {urls_file} -- skipping URL ingestion.")
        return []

    with open(urls_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    saved_paths = []
    for url in urls:
        path = fetch_and_convert(url)
        if path:
            saved_paths.append(path)

    print(f"[web_loader] Converted {len(saved_paths)}/{len(urls)} URLs to markdown")
    return saved_paths


if __name__ == "__main__":
    ingest_urls_from_file()
