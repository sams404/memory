#!/usr/bin/env python3
"""
Universal Information Pipeline
Semantic sorting + auto-linking for Obsidian, Notion, NotebookLM
Handles: photos, text, files, audio, links, books
"""

import os
import sys
import base64
import json
import mimetypes
import re
import urllib.request
from datetime import datetime
from pathlib import Path

import anthropic

# ─── CONFIG ───────────────────────────────────────────────────────────────────

VAULT_PATH   = Path(os.environ.get("VAULT_PATH", Path.home() / "vault"))
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_DB_ID = os.environ.get("NOTION_DB_ID", "")
MODEL        = "claude-opus-4-6"

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
- Finance & investing (Norway: aksjesparekonto, DNB, Vipps)
- AI projects and automation
- English and Norwegian language learning
- Online business and income streams
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

def extract_image_b64(path: Path) -> tuple[str, str]:
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    data = base64.standard_b64encode(path.read_bytes()).decode()
    return data, mime

def extract_audio(path: Path) -> str:
    try:
        import whisper
        print("   Transcribing audio...")
        result = whisper.load_model("base").transcribe(str(path))
        return result["text"]
    except ImportError:
        return f"[Audio: {path.name} — pip install openai-whisper]"

def extract_pdf(path: Path) -> str:
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:50]:
                text += page.extract_text() or ""
        return text
    except ImportError:
        try:
            import pypdf
            return "\n".join(p.extract_text() for p in pypdf.PdfReader(str(path)).pages[:50])
        except ImportError:
            return f"[PDF: {path.name} — pip install pdfplumber]"

def extract_url(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode(errors="ignore")
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text)[:8000]
    except Exception as e:
        return f"[Fetch failed: {e}]"

# ─── SEMANTIC LINKING ─────────────────────────────────────────────────────────

def get_vault_index() -> str:
    """Read titles + insights of existing notes for semantic comparison."""
    index = []
    for md in VAULT_PATH.rglob("*.md"):
        if md.name == "PROFILE.md":
            continue
        content = md.read_text(errors="ignore")
        title_m = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
        insight_m = re.search(r"## Key Insight\n(.+)", content)
        summary_m = re.search(r"## Summary\n((?:- .+\n?)+)", content)
        if title_m:
            entry = f"[[{md.stem}]] — {title_m.group(1).strip()}"
            if insight_m:
                entry += f": {insight_m.group(1).strip()}"
            elif summary_m:
                entry += f": {summary_m.group(1).strip().split(chr(10))[0]}"
            index.append(entry)
    return "\n".join(index[-80:])

def find_semantic_links(analysis: dict) -> list[str]:
    """Use Claude to find conceptually related existing notes."""
    vault_index = get_vault_index()
    if not vault_index:
        return []

    prompt = f"""Find notes semantically related to this new note by CONCEPT or THEME.

NEW NOTE:
Title: {analysis.get('title')}
Category: {analysis.get('category')}
Tags: {analysis.get('tags')}
Insight: {analysis.get('key_insight')}

EXISTING NOTES:
{vault_index}

Return ONLY a JSON array of 2-4 note stems (no [[brackets]]):
["note-stem-1", "note-stem-2"]

Return [] if nothing is truly related."""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}]
    )
    text = resp.content[0].text
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if match:
        try:
            return [f"[[{l}]]" for l in json.loads(match.group()) if l]
        except Exception:
            pass
    return []

# ─── CLAUDE ANALYSIS ──────────────────────────────────────────────────────────

def analyze_text(content: str, source_hint: str = "") -> dict:
    prompt = f"""Analyze this content for a personal knowledge vault.

USER INTERESTS:
{USER_INTERESTS}

SOURCE: {source_hint}
CONTENT:
{content[:6000]}

Return ONLY valid JSON:
{{
  "title": "descriptive title (max 8 words)",
  "category": "finance|ai|language|project|knowledge|journal",
  "tags": ["tag1", "tag2", "tag3"],
  "relevance": 1-10,
  "action_required": true|false,
  "summary": ["point 1", "point 2", "point 3"],
  "key_insight": "one sentence core takeaway",
  "notion_status": "To Process|In Progress|Done|Reference"
}}"""

    with client.messages.stream(
        model=MODEL,
        max_tokens=1024,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        text = stream.get_final_message().content[-1].text

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"title": "Untitled", "category": "inbox", "tags": [], "relevance": 5,
            "action_required": False, "summary": [], "key_insight": "",
            "notion_status": "To Process"}

def analyze_image(b64: str, mime: str) -> dict:
    with client.messages.stream(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
            {"type": "text", "text": f"""Analyze this image for a personal knowledge vault.

USER INTERESTS:
{USER_INTERESTS}

Return ONLY valid JSON:
{{
  "title": "descriptive title",
  "category": "finance|ai|language|project|knowledge|journal",
  "tags": ["tag1", "tag2"],
  "relevance": 1-10,
  "action_required": true|false,
  "extracted_text": "all visible text in image",
  "summary": ["what this shows"],
  "key_insight": "one sentence takeaway",
  "notion_status": "To Process|Reference"
}}"""}
        ]}],
    ) as stream:
        text = stream.get_final_message().content[-1].text

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"title": "Image", "category": "inbox", "tags": [], "relevance": 5,
            "action_required": False, "extracted_text": "", "summary": [],
            "key_insight": "", "notion_status": "To Process"}

# ─── NOTE BUILDER ─────────────────────────────────────────────────────────────

def build_note(analysis: dict, source: str, raw: str, links: list[str]) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    summary = "\n".join(f"- {s}" for s in analysis.get("summary", []))

    note = f"""---
title: {analysis.get('title', 'Untitled')}
date: {date}
type: {analysis.get('category', 'inbox')}
tags: [{', '.join(analysis.get('tags', []))}]
source: {source}
relevance: {analysis.get('relevance', 5)}/10
action_required: {str(analysis.get('action_required', False)).lower()}
status: new
---

## Summary
{summary}

## Key Insight
{analysis.get('key_insight', '')}
"""
    if analysis.get("extracted_text"):
        note += f"\n## Extracted Text\n{analysis['extracted_text']}\n"

    if links:
        note += "\n## Related\n" + "\n".join(links) + "\n"

    if raw and len(raw) < 1500:
        note += f"\n## Source\n{raw}\n"

    return note

# ─── NOTION INTEGRATION ───────────────────────────────────────────────────────

def push_to_notion(analysis: dict, source: str, note_file: str):
    if not NOTION_TOKEN or not NOTION_DB_ID:
        return

    props = {
        "Name": {"title": [{"text": {"content": analysis.get("title", "Untitled")}}]},
        "Category": {"select": {"name": analysis.get("category", "inbox").capitalize()}},
        "Tags": {"multi_select": [{"name": t} for t in analysis.get("tags", [])[:5]]},
        "Relevance": {"number": analysis.get("relevance", 5)},
        "Action Required": {"checkbox": bool(analysis.get("action_required"))},
        "Status": {"select": {"name": analysis.get("notion_status", "To Process")}},
        "Insight": {"rich_text": [{"text": {"content": analysis.get("key_insight", "")[:2000]}}]},
        "Obsidian": {"rich_text": [{"text": {"content": note_file}}]},
    }
    if source.startswith("http"):
        props["Source"] = {"url": source}

    data = json.dumps({"parent": {"database_id": NOTION_DB_ID}, "properties": props}).encode()
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=data,
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        },
        method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print("   Notion: synced ✓")
    except Exception as e:
        print(f"   Notion: failed — {e}")

# ─── MAIN PROCESSOR ───────────────────────────────────────────────────────────

def process(input_str: str) -> Path:
    ensure_vault()
    path = Path(input_str)
    is_url = input_str.startswith(("http://", "https://"))

    print(f"\n▶ {input_str[:70]}")

    if path.exists() and path.is_file():
        suffix = path.suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
            print("  Type: Image")
            b64, mime = extract_image_b64(path)
            analysis = analyze_image(b64, mime)
            source, raw = str(path), analysis.get("extracted_text", "")
        elif suffix in {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}:
            print("  Type: Audio")
            transcript = extract_audio(path)
            analysis = analyze_text(transcript, f"audio: {path.name}")
            source, raw = str(path), transcript[:1500]
        elif suffix == ".pdf":
            print("  Type: PDF")
            text = extract_pdf(path)
            analysis = analyze_text(text, f"pdf: {path.name}")
            source, raw = str(path), text[:1500]
        else:
            print("  Type: File")
            text = path.read_text(errors="ignore")
            analysis = analyze_text(text, f"file: {path.name}")
            source, raw = str(path), text[:1500]
    elif is_url:
        print("  Type: URL")
        text = extract_url(input_str)
        analysis = analyze_text(text, f"url: {input_str}")
        source, raw = input_str, text[:1500]
    else:
        print("  Type: Text")
        analysis = analyze_text(input_str, "direct input")
        source, raw = "direct input", input_str

    print("  Finding semantic links...")
    links = find_semantic_links(analysis)

    note = build_note(analysis, source, raw, links)
    out = note_path(analysis.get("category", "inbox"), analysis.get("title", "note"))
    out.write_text(note)

    push_to_notion(analysis, source, out.name)

    folder = FOLDER_MAP.get(analysis.get("category", "inbox"), "00-Inbox")
    print(f"""
✓ Saved
  Title:     {analysis.get('title')}
  Folder:    {folder}
  Relevance: {analysis.get('relevance')}/10
  Action:    {'YES ⚡' if analysis.get('action_required') else 'no'}
  Links:     {', '.join(links) if links else 'none found'}
  File:      {out.name}""")

    return out


def main():
    if len(sys.argv) < 2:
        print("""
Usage:
  python pipeline.py <input>

  photo.jpg / voice.m4a / doc.pdf / https://... / "any text"

  Multiple:
  python pipeline.py file1.pdf photo.jpg https://... "idea"

Env vars:
  VAULT_PATH        path to Obsidian vault (default: ~/vault)
  ANTHROPIC_API_KEY
  NOTION_TOKEN      optional
  NOTION_DB_ID      optional
""")
        sys.exit(1)

    for inp in sys.argv[1:]:
        try:
            process(inp.strip())
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback; traceback.print_exc()


if __name__ == "__main__":
    main()
