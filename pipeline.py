#!/usr/bin/env python3
"""
Universal Information Pipeline
Handles: photos, text, files, audio, links, books
Outputs: Obsidian vault notes with analysis
"""

import os
import sys
import base64
import json
import mimetypes
import hashlib
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic

# ─── CONFIG ───────────────────────────────────────────────────────────────────

VAULT_PATH = Path(os.environ.get("VAULT_PATH", Path.home() / "vault"))
MODEL = "claude-opus-4-6"
PROFILE_PATH = VAULT_PATH / "PROFILE.md"

FOLDER_MAP = {
    "finance":   "01-Finance",
    "ai":        "02-AI",
    "language":  "03-Languages",
    "project":   "04-Projects",
    "knowledge": "05-Knowledge",
    "journal":   "06-Journal",
    "inbox":     "00-Inbox",
}

USER_INTERESTS = """
- Finance & investing (Norway context: aksjesparekonto, DNB, Vipps)
- AI projects and automation
- English and Norwegian language learning
- Online business
"""

client = anthropic.Anthropic()

# ─── VAULT SETUP ──────────────────────────────────────────────────────────────

def ensure_vault():
    for folder in FOLDER_MAP.values():
        (VAULT_PATH / folder).mkdir(parents=True, exist_ok=True)

def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_-]+", "-", text).strip("-")[:50]

def note_path(category: str, title: str) -> Path:
    date = datetime.now().strftime("%Y-%m-%d")
    folder = FOLDER_MAP.get(category, FOLDER_MAP["inbox"])
    return VAULT_PATH / folder / f"{date}-{slugify(title)}.md"

# ─── INPUT EXTRACTION ─────────────────────────────────────────────────────────

def extract_text_file(path: Path) -> str:
    return path.read_text(errors="ignore")

def extract_image_b64(path: Path) -> tuple[str, str]:
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    data = base64.standard_b64encode(path.read_bytes()).decode()
    return data, mime

def extract_audio(path: Path) -> str:
    """Transcribe audio using whisper."""
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(str(path))
        return result["text"]
    except ImportError:
        return f"[Audio file: {path.name} — install whisper: pip install openai-whisper]"

def extract_pdf(path: Path) -> str:
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:50]:  # max 50 pages
                text += page.extract_text() or ""
        return text
    except ImportError:
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            return "\n".join(p.extract_text() for p in reader.pages[:50])
        except ImportError:
            return f"[PDF: {path.name} — install: pip install pdfplumber]"

def extract_url(url: str) -> str:
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode(errors="ignore")
        # strip tags
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text[:8000]
    except Exception as e:
        return f"[Fetch failed: {e}]"

# ─── CLAUDE ANALYSIS ──────────────────────────────────────────────────────────

def analyze_text(content: str, source_hint: str = "") -> dict:
    """Classify, summarize, and score relevance."""
    prompt = f"""You are analyzing content for a personal knowledge vault.

USER INTERESTS:
{USER_INTERESTS}

SOURCE HINT: {source_hint}

CONTENT:
{content[:6000]}

Respond with ONLY valid JSON:
{{
  "title": "short descriptive title (max 8 words)",
  "category": "finance|ai|language|project|knowledge|journal",
  "tags": ["tag1", "tag2"],
  "relevance": 1-10,
  "action_required": true|false,
  "summary": ["bullet 1", "bullet 2", "bullet 3"],
  "key_insight": "one sentence takeaway"
}}"""

    with client.messages.stream(
        model=MODEL,
        max_tokens=1024,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        text = stream.get_final_message().content[-1].text

    # extract JSON
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"title": "Untitled", "category": "inbox", "tags": [], "relevance": 5,
            "action_required": False, "summary": [text[:200]], "key_insight": ""}

def analyze_image(b64: str, mime: str) -> dict:
    """Analyze image content with Claude Vision."""
    with client.messages.stream(
        model=MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime, "data": b64}
                },
                {
                    "type": "text",
                    "text": f"""Analyze this image for a personal knowledge vault.

USER INTERESTS:
{USER_INTERESTS}

Extract all text visible. Describe what you see. Classify and summarize.

Respond with ONLY valid JSON:
{{
  "title": "short descriptive title",
  "category": "finance|ai|language|project|knowledge|journal",
  "tags": ["tag1", "tag2"],
  "relevance": 1-10,
  "action_required": true|false,
  "extracted_text": "all text visible in image",
  "summary": ["what this image shows"],
  "key_insight": "one sentence takeaway"
}}"""
                }
            ]
        }],
    ) as stream:
        text = stream.get_final_message().content[-1].text

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"title": "Image", "category": "inbox", "tags": [], "relevance": 5,
            "action_required": False, "extracted_text": "", "summary": [], "key_insight": ""}

# ─── NOTE BUILDER ─────────────────────────────────────────────────────────────

def build_note(analysis: dict, source: str, raw_content: str = "") -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    tags = " ".join(f"#{t}" for t in analysis.get("tags", []))
    summary_bullets = "\n".join(f"- {s}" for s in analysis.get("summary", []))
    action = "true" if analysis.get("action_required") else "false"

    frontmatter = f"""---
title: {analysis.get('title', 'Untitled')}
date: {date}
type: {analysis.get('category', 'inbox')}
tags: [{', '.join(analysis.get('tags', []))}]
source: {source}
relevance: {analysis.get('relevance', 5)}/10
action_required: {action}
status: new
---"""

    body = f"""
## Summary
{summary_bullets}

## Key Insight
{analysis.get('key_insight', '')}
"""

    if analysis.get("extracted_text"):
        body += f"\n## Extracted Text\n{analysis['extracted_text']}\n"

    if raw_content and len(raw_content) < 2000:
        body += f"\n## Source Content\n{raw_content[:2000]}\n"

    return frontmatter + body

# ─── FIND RELATED NOTES ───────────────────────────────────────────────────────

def find_related(tags: list[str], title: str) -> list[str]:
    related = []
    keywords = tags + title.lower().split()[:3]
    for md in VAULT_PATH.rglob("*.md"):
        content = md.read_text(errors="ignore").lower()
        if any(kw in content for kw in keywords):
            related.append(f"[[{md.stem}]]")
        if len(related) >= 3:
            break
    return related

# ─── MAIN PROCESSOR ───────────────────────────────────────────────────────────

def process(input_str: str) -> Path:
    """Process any input: file path, URL, or raw text."""
    ensure_vault()
    path = Path(input_str)
    is_url = input_str.startswith(("http://", "https://"))

    print(f"\n Processing: {input_str[:60]}...")

    # ── Detect type ──
    if path.exists() and path.is_file():
        suffix = path.suffix.lower()

        if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
            print("   Type: Image")
            b64, mime = extract_image_b64(path)
            analysis = analyze_image(b64, mime)
            source = str(path)
            raw = analysis.get("extracted_text", "")

        elif suffix in {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}:
            print("   Type: Audio — transcribing...")
            transcript = extract_audio(path)
            analysis = analyze_text(transcript, source_hint=f"audio: {path.name}")
            source = str(path)
            raw = transcript[:2000]

        elif suffix == ".pdf":
            print("   Type: PDF")
            text = extract_pdf(path)
            analysis = analyze_text(text, source_hint=f"pdf: {path.name}")
            source = str(path)
            raw = text[:2000]

        elif suffix in {".txt", ".md", ".rst", ".csv", ".json", ".html"}:
            print("   Type: Text file")
            text = extract_text_file(path)
            analysis = analyze_text(text, source_hint=f"file: {path.name}")
            source = str(path)
            raw = text[:2000]

        elif suffix in {".epub", ".mobi"}:
            print("   Type: Book — processing as text")
            text = extract_text_file(path)
            analysis = analyze_text(text[:10000], source_hint=f"book: {path.name}")
            source = str(path)
            raw = text[:2000]

        else:
            print("   Type: Unknown file — treating as text")
            text = extract_text_file(path)
            analysis = analyze_text(text, source_hint=path.name)
            source = str(path)
            raw = text[:2000]

    elif is_url:
        print("   Type: URL — fetching...")
        text = extract_url(input_str)
        analysis = analyze_text(text, source_hint=f"url: {input_str}")
        source = input_str
        raw = text[:2000]

    else:
        print("   Type: Text / Thought")
        analysis = analyze_text(input_str, source_hint="direct input")
        source = "direct input"
        raw = input_str

    # ── Build & save note ──
    related = find_related(analysis.get("tags", []), analysis.get("title", ""))
    note = build_note(analysis, source, raw)
    if related:
        note += f"\n## Related\n" + "\n".join(related) + "\n"

    out_path = note_path(analysis.get("category", "inbox"), analysis.get("title", "note"))
    out_path.write_text(note)

    # ── Report ──
    relevance = analysis.get("relevance", 0)
    print(f"\n DONE")
    print(f"   Title:     {analysis.get('title')}")
    print(f"   Category:  {analysis.get('category')} ({FOLDER_MAP.get(analysis.get('category','inbox'),'00-Inbox')})")
    print(f"   Relevance: {relevance}/10")
    print(f"   Action:    {'YES' if analysis.get('action_required') else 'no'}")
    print(f"   Saved:     {out_path}")

    if relevance < 4:
        print(f"   ⚠  Low relevance ({relevance}/10) — saved to inbox anyway")

    return out_path


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("""
Usage:
  python pipeline.py <input>

Input can be:
  - File path:   /path/to/photo.jpg
  - URL:         https://example.com/article
  - Text:        "My idea about X..."
  - Multiple:    python pipeline.py file1.pdf file2.jpg https://...

Environment:
  VAULT_PATH   Path to Obsidian vault (default: ~/vault)
  ANTHROPIC_API_KEY  Your API key
""")
        sys.exit(1)

    for inp in sys.argv[1:]:
        try:
            process(inp.strip())
        except Exception as e:
            print(f"\n  Error processing '{inp}': {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
