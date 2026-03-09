#!/usr/bin/env python3
"""
Structured Memory Pipeline — Personal Growth System
Diary + semantic linking + pattern recognition
"""

import os, sys, re, json, base64, mimetypes, urllib.request, tempfile
from datetime import datetime
from pathlib import Path
import anthropic

# ─── CONFIG ───────────────────────────────────
VAULT   = Path(os.environ.get("VAULT_PATH", Path.home() / "vault"))
MODEL   = "claude-opus-4-6"
client  = anthropic.Anthropic()

FOLDERS = {
    "journal":   "01-Journal",
    "goal":      "02-Goals",
    "win":       "03-Wins",
    "lesson":    "04-Lessons",
    "knowledge": "05-Knowledge",
    "review":    "06-Reviews",
    "inbox":     "00-Inbox",
}

PROFILE = """
Name: Samson
Location: Norway
Focus areas: Finance (aksjesparekonto, investing), AI automation, English & Norwegian
Core goal: Intellectual growth + financial freedom through technology
Values: Discipline, minimal action, hyperFocus, progress over perfection
"""

# ─── VAULT SETUP ──────────────────────────────
def ensure_vault():
    for f in FOLDERS.values():
        (VAULT / f).mkdir(parents=True, exist_ok=True)

def slugify(t):
    return re.sub(r"[\s_-]+", "-", re.sub(r"[^\w\s-]", "", t.lower())).strip("-")[:50]

def note_path(cat, title):
    d = datetime.now().strftime("%Y-%m-%d")
    return VAULT / FOLDERS.get(cat, "00-Inbox") / f"{d}-{slugify(title)}.md"

# ─── TEMPLATES ────────────────────────────────
TEMPLATES = {
    "journal": """## How I feel
{mood}

## What happened today
{content}

## Key insight
{key_insight}

## What I'm grateful for
-

## Tomorrow's focus
-
""",
    "goal": """## Goal
{content}

## Why it matters
{key_insight}

## Milestones
- [ ]

## Progress
-
""",
    "win": """## The Win
{content}

## Why it matters
{key_insight}

## What made it possible
-

## How to repeat this
-
""",
    "lesson": """## What happened
{content}

## The lesson
{key_insight}

## How I'll apply this
-

## Related patterns
-
""",
    "knowledge": """## Summary
{content}

## Key insight
{key_insight}

## How this applies to me
-
""",
}

# ─── INPUT EXTRACTION ─────────────────────────
def extract_image(path):
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    return base64.standard_b64encode(path.read_bytes()).decode(), mime

def extract_audio(path):
    try:
        import whisper
        return whisper.load_model("base").transcribe(str(path))["text"]
    except ImportError:
        return f"[Audio — pip install openai-whisper]"

def extract_pdf(path):
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages[:50])
    except ImportError:
        return path.read_text(errors="ignore")

def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode(errors="ignore")
        text = re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.DOTALL))
        return re.sub(r"\s+", " ", text)[:8000]
    except Exception as e:
        return f"[Fetch failed: {e}]"

# ─── SEMANTIC INDEX ────────────────────────────
def vault_index():
    entries = []
    for md in VAULT.rglob("*.md"):
        if md.name == "PROFILE.md": continue
        c = md.read_text(errors="ignore")
        t = re.search(r"^title:\s*(.+)$", c, re.MULTILINE)
        i = re.search(r"## Key insight\n(.+)", c, re.IGNORECASE)
        if t:
            entries.append(f"[[{md.stem}]] {t.group(1).strip()}: {i.group(1).strip() if i else ''}")
    return "\n".join(entries[-100:])

def semantic_links(analysis):
    idx = vault_index()
    if not idx: return []
    resp = client.messages.create(
        model=MODEL, max_tokens=200,
        messages=[{"role": "user", "content": f"""Find 2-3 notes semantically related by CONCEPT to:
Title: {analysis.get('title')}
Insight: {analysis.get('key_insight')}
Category: {analysis.get('category')}

VAULT:
{idx}

Return JSON array of stems only: ["stem-1", "stem-2"]
Return [] if nothing truly related."""}]
    )
    m = re.search(r"\[.*?\]", resp.content[0].text, re.DOTALL)
    try: return [f"[[{l}]]" for l in json.loads(m.group()) if l] if m else []
    except: return []

# ─── CLAUDE ANALYSIS ──────────────────────────
def analyze(content, source="", is_image=False, b64=None, mime=None):
    if is_image:
        messages = [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
            {"type": "text", "text": f"""Analyze this image for a personal growth journal.

PROFILE:
{PROFILE}

Extract all visible text. Understand what this means for personal growth.

Return ONLY JSON:
{{
  "title": "title max 7 words",
  "category": "journal|goal|win|lesson|knowledge",
  "tags": ["tag1", "tag2"],
  "mood": "energized|focused|reflective|uncertain|grateful|motivated",
  "relevance": 1-10,
  "action_required": true|false,
  "extracted_text": "all text in image",
  "content": "what this image shows/means",
  "key_insight": "one sentence growth insight"
}}"""}
        ]}]
    else:
        messages = [{"role": "user", "content": f"""Analyze for personal growth journal.

PROFILE:
{PROFILE}

SOURCE: {source}
CONTENT:
{content[:5000]}

Return ONLY JSON:
{{
  "title": "title max 7 words",
  "category": "journal|goal|win|lesson|knowledge",
  "tags": ["tag1", "tag2"],
  "mood": "energized|focused|reflective|uncertain|grateful|motivated",
  "relevance": 1-10,
  "action_required": true|false,
  "content": "key content summary",
  "key_insight": "one sentence growth insight"
}}"""}]

    with client.messages.stream(
        model=MODEL, max_tokens=1024,
        thinking={"type": "adaptive"},
        messages=messages
    ) as s:
        text = s.get_final_message().content[-1].text

    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try: return json.loads(m.group())
        except: pass
    return {"title": "Untitled", "category": "inbox", "tags": [], "mood": "",
            "relevance": 5, "action_required": False, "content": text[:200], "key_insight": ""}

# ─── NOTE BUILDER ─────────────────────────────
def build_note(a, source, raw, links):
    date = datetime.now().strftime("%Y-%m-%d")
    cat  = a.get("category", "inbox")
    tmpl = TEMPLATES.get(cat, TEMPLATES["knowledge"])

    body = tmpl.format(
        content     = a.get("content", raw[:500]),
        key_insight = a.get("key_insight", ""),
        mood        = a.get("mood", ""),
    )

    note = f"""---
title: {a.get('title', 'Untitled')}
date: {date}
type: {cat}
tags: [{', '.join(a.get('tags', []))}]
mood: {a.get('mood', '')}
source: {source}
relevance: {a.get('relevance', 5)}/10
action_required: {str(a.get('action_required', False)).lower()}
status: new
---
{body}"""

    if a.get("extracted_text"):
        note += f"\n## Extracted Text\n{a['extracted_text']}\n"
    if links:
        note += "\n## Related\n" + "\n".join(links) + "\n"

    return note

# ─── PROCESS ──────────────────────────────────
def process(inp):
    ensure_vault()
    path   = Path(inp)
    is_url = inp.startswith(("http://", "https://"))
    print(f"\n▶ {inp[:70]}")

    if path.exists() and path.is_file():
        sx = path.suffix.lower()
        if sx in {".jpg",".jpeg",".png",".gif",".webp",".bmp"}:
            print("  Image"); b64, mime = extract_image(path)
            a = analyze("", is_image=True, b64=b64, mime=mime)
            source, raw = str(path), a.get("extracted_text","")
        elif sx in {".mp3",".wav",".m4a",".ogg",".flac"}:
            print("  Audio"); t = extract_audio(path)
            a = analyze(t, f"audio:{path.name}"); source, raw = str(path), t[:1000]
        elif sx == ".pdf":
            print("  PDF"); t = extract_pdf(path)
            a = analyze(t, f"pdf:{path.name}"); source, raw = str(path), t[:1000]
        else:
            print("  File"); t = path.read_text(errors="ignore")
            a = analyze(t, path.name); source, raw = str(path), t[:1000]
    elif is_url:
        print("  URL"); t = fetch_url(inp)
        a = analyze(t, inp); source, raw = inp, t[:1000]
    else:
        print("  Text"); a = analyze(inp, "direct")
        source, raw = "direct", inp

    print("  Linking semantically...")
    links = semantic_links(a)
    note  = build_note(a, source, raw, links)
    out   = note_path(a.get("category","inbox"), a.get("title","note"))
    out.write_text(note)

    folder = FOLDERS.get(a.get("category","inbox"), "00-Inbox")
    print(f"""
✓ Saved
  Title:   {a.get('title')}
  Folder:  {folder}
  Mood:    {a.get('mood','-')}
  Score:   {a.get('relevance')}/10
  Links:   {', '.join(links) if links else 'none'}
  Action:  {'⚡ YES' if a.get('action_required') else 'no'}""")
    return out

def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <file|url|text> [...]"); sys.exit(1)
    for inp in sys.argv[1:]:
        try: process(inp.strip())
        except Exception as e:
            import traceback; print(f"\n✗ {e}"); traceback.print_exc()

if __name__ == "__main__":
    main()
