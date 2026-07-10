"""
youtube_loader.py
-------------------
Fetches transcripts from PUBLIC YouTube videos and saves them as Documents.
Only use this for openly published videos -- not paywalled course platforms.
"""

import os
import re
from langchain_core.documents import Document


def _extract_video_id(url):
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    return match.group(1) if match else None


def load_youtube_transcript(url):
    from youtube_transcript_api import YouTubeTranscriptApi

    video_id = _extract_video_id(url)
    if not video_id:
        print("[youtube_loader] Could not extract video ID from:", url)
        return None

    try:
        ytt_api = YouTubeTranscriptApi()
        fetched = ytt_api.fetch(video_id)
        full_text = " ".join(snippet.text for snippet in fetched)
    except Exception as e:
        print("[youtube_loader] Failed to fetch transcript for", url, ":", e)
        return None

    return Document(
        page_content=full_text,
        metadata={"source": url, "source_type": "youtube"},
    )


def load_youtube_urls_from_file(filepath="data/youtube_urls.txt"):
    if not os.path.exists(filepath):
        print("[youtube_loader] No file found at", filepath)
        return []

    # utf-8-sig strips a leading byte-order-mark so it can't corrupt the first URL.
    with open(filepath, "r", encoding="utf-8-sig") as f:
        urls = [
            line.strip().lstrip("﻿")
            for line in f
            if line.strip() and not line.lstrip("﻿").startswith("#")
        ]

    docs = []
    for url in urls:
        doc = load_youtube_transcript(url)
        if doc:
            docs.append(doc)

    print("[youtube_loader] Loaded", len(docs), "YouTube transcripts")
    return docs


if __name__ == "__main__":
    load_youtube_urls_from_file()