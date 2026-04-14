"""
fetch_transcripts.py
--------------------
Extracts transcripts for every video in a YouTube playlist and saves each
one as a plain-text file under raw/.

Dependencies (install once):
    pip install yt-dlp youtube-transcript-api

Usage:
    python fetch_transcripts.py "https://www.youtube.com/playlist?list=PLxxxxxxx"

Each video produces a file like:
    raw/001_<video-title>.txt
    raw/002_<video-title>.txt
    ...

The transcript text is written as-is (no timestamps) so it can be fed
directly into the literary-summary pipeline.
"""

import sys
import os
import re
import json
import subprocess

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str, max_len: int = 60) -> str:
    """Turn a video title into a safe filename fragment."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text[:max_len]


def get_playlist_entries(playlist_url: str) -> list[dict]:
    """
    Use yt-dlp to fetch playlist metadata (no download).
    Returns a list of dicts with keys: id, title, url
    """
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        playlist_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    entries = []
    for entry in data.get("entries", []):
        video_id = entry.get("id") or entry.get("url", "").split("v=")[-1]
        title = entry.get("title", video_id)
        entries.append({"id": video_id, "title": title})
    return entries


def fetch_transcript(video_id: str) -> str:
    """
    Fetch the transcript for a single video via youtube-transcript-api.
    Tries the manually uploaded transcript first, then auto-generated.
    Returns plain text (no timestamps).
    """
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound

    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        # Prefer manually created English transcript
        try:
            transcript = transcript_list.find_manually_created_transcript(["en"])
        except NoTranscriptFound:
            # Fall back to auto-generated English
            try:
                transcript = transcript_list.find_generated_transcript(["en"])
            except NoTranscriptFound:
                # Last resort: take whatever is available and translate to English
                transcript = next(iter(transcript_list)).translate("en")

        segments = transcript.fetch()
        return " ".join(seg.text for seg in segments)

    except Exception as exc:
        return f"[TRANSCRIPT UNAVAILABLE: {exc}]"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_transcripts.py <playlist_url>")
        sys.exit(1)

    playlist_url = sys.argv[1]
    out_dir = os.path.join(os.path.dirname(__file__), "raw")
    os.makedirs(out_dir, exist_ok=True)

    print(f"Fetching playlist metadata from: {playlist_url}")
    try:
        entries = get_playlist_entries(playlist_url)
    except subprocess.CalledProcessError as exc:
        print(f"yt-dlp failed: {exc.stderr}")
        sys.exit(1)

    print(f"Found {len(entries)} video(s).\n")

    for idx, entry in enumerate(entries, start=1):
        video_id = entry["id"]
        title = entry["title"]
        slug = slugify(title)
        filename = f"{idx:03d}_{slug}.txt"
        filepath = os.path.join(out_dir, filename)

        if os.path.exists(filepath):
            print(f"[{idx}/{len(entries)}] Skipping (already exists): {filename}")
            continue

        print(f"[{idx}/{len(entries)}] {title}")
        print(f"           id: {video_id}")

        text = fetch_transcript(video_id)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(text)
            f.write("\n")

        status = "UNAVAILABLE" if text.startswith("[TRANSCRIPT UNAVAILABLE") else f"{len(text):,} chars"
        print(f"           -> {filename} ({status})\n")

    print("Done. Transcripts saved to raw/")


if __name__ == "__main__":
    main()
