#!/usr/bin/env python3
"""
Structured Memory Pipeline — Personal Growth System
Powered by Groq (free)
"""

import os, sys, re, json, base64, mimetypes, urllib.request
from datetime import datetime
from pathlib import Path
from groq import Groq

VAULT  = Path(os.environ.get("VAULT_PATH", Path.home() / "vault"))
MODEL  = "llama-3.3-70b-versatile"
client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

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
Name: Samson, lives in Norway
Focus: Finance (aksjesparekonto, investing), AI automation, English & Norwegian
Goal: Financial freedom + intellectual growth through technology
Values: Discipline, small consistent actions, hyperFocus
"""

TEMPLATES = {
    "journal":   "## How I feel\n{mood}\n\n## What happened\n{content}\n\n## Key insight\n{key_insight}\n\n## Grateful for\n-\n\n## Tomorrow's focus\n-\n",
    "goal":      "## Goal\n{content}\n\n## Why it matters\n{key_insight}\n\n## Milestones\n- [ ]\n\n## Progress\n-\n",
    "win":       "## The Win\n{content}\n\n## Why it matters\n{key_insight}\n\n## What made it possible\n-\n\n## How to repeat\n-\n",
    "lesson":    "## What happened\n{content}\n\n## The lesson\n{key_insight}\n\n## How I'll apply this\n-\n",
    "knowledge": "## Summary\n{content}\n\n## Key insight\n{key_insight}\n\n## How this applies to me\n-\n",
}

def ensure_vault():
    VAULT.mkdir(parents=True, exist_ok=True)
    for f in FOLDERS.values():
        (VAULT / f).mkdir(parents=True, exist_ok=True)

def slugify(t):
    return re.sub(r"[\s_-]+", "-", re.sub(r"[^\w\s-]", "", t.lower())).strip("-")[:50]

def note_path(cat, title):
    d = datetime.now().strftime("%Y-%m-%d")
    return VAULT / FOLDERS.get(cat, "00-Inbox") / f"{d}-{slugify(title)}.md"

def extract_audio(path):
    try:
        import whisper
        return whisper.load_model("base").transcribe(str(path))["text"]
    except ImportError:
        return "[Audio — pip install openai-whisper]"

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

def extract_image(path):
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    data = base64.standard_b64encode(path.read_bytes()).decode()
    return data, mime

def vault_index():
    entries = []
    for md in VAULT.rglob("*.md"):
        if md.name == "PROFILE.md": continue
        c = md.read_text(errors="ignore")
        t = re.search(r"^title:\s*(.+)$", c, re.MULTILINE)
        i = re.search(r"## Key insight\n(.+)", c, re.IGNORECASE)
        if t:
            entries.append(f"[[{md.stem}]] {t.group(1).strip()}: {i.group(1).strip() if i else ''}")
    return "\n".join(entries[-80:])

def semantic_links(analysis):
    idx = vault_index()
    if not idx: return []
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"""Find 2-3 notes semantically related by CONCEPT to:
Title: {analysis.get('title')}
Insight: {analysis.get('key_insight')}

VAULT:
{idx}

Return JSON array only: ["stem-1", "stem-2"] or []"""}],
            max_tokens=100
        )
        m = re.search(r"\[.*?\]", resp.choices[0].message.content, re.DOTALL)
        return [f"[[{l}]]" for l in json.loads(m.group()) if l] if m else []
    except: return []

def analyze(content, source="", image_b64=None, image_mime=None):
    messages = []
    if image_b64:
        messages = [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{image_b64}"}},
            {"type": "text", "text": f"""Analyze this image for personal growth journal.
PROFILE: {PROFILE}
Return ONLY valid JSON:
{{"title":"title max 7 words","category":"journal|goal|win|lesson|knowledge","tags":["tag1"],"mood":"energized|focused|reflective|uncertain|grateful|motivated","relevance":8,"action_required":false,"content":"what this shows","key_insight":"one sentence growth insight"}}"""}
        ]}]
    else:
        messages = [{"role": "user", "content": f"""Analyze for personal growth journal.

PROFILE:
{PROFILE}

SOURCE: {source}
CONTENT:
{content[:4000]}

Return ONLY valid JSON (no markdown):
{{"title":"title max 7 words","category":"journal|goal|win|lesson|knowledge","tags":["tag1","tag2"],"mood":"energized|focused|reflective|uncertain|grateful|motivated","relevance":8,"action_required":false,"content":"2-3 sentence summary","key_insight":"one sentence growth insight"}}"""}]

    try:
        resp = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=512)
        text = resp.choices[0].message.content
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m: return json.loads(m.group())
    except Exception as e:
        print(f"  Analysis error: {e}")

    return {"title": "Untitled", "category": "inbox", "tags": [], "mood": "",
            "relevance": 5, "action_required": False, "content": content[:200], "key_insight": ""}

def build_note(a, source, raw, links):
    date = datetime.now().strftime("%Y-%m-%d")
    cat  = a.get("category", "inbox")
    body = TEMPLATES.get(cat, TEMPLATES["knowledge"]).format(
        content=a.get("content", raw[:500]),
        key_insight=a.get("key_insight", ""),
        mood=a.get("mood", ""),
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
    if links:
        note += "\n## Related\n" + "\n".join(links) + "\n"
    return note

def process(inp):
    ensure_vault()
    path   = Path(inp)
    is_url = inp.startswith(("http://", "https://"))
    print(f"\n▶ {inp[:70]}")

    if path.exists() and path.is_file():
        sx = path.suffix.lower()
        if sx in {".jpg",".jpeg",".png",".gif",".webp",".bmp"}:
            print("  Image")
            b64, mime = extract_image(path)
            a = analyze("", image_b64=b64, image_mime=mime)
            source, raw = str(path), a.get("content","")
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

    print(f"""
✓ Saved
  Title:   {a.get('title')}
  Folder:  {FOLDERS.get(a.get('category','inbox'), '00-Inbox')}
  Mood:    {a.get('mood','-')}
  Score:   {a.get('relevance')}/10
  Links:   {', '.join(links) if links else 'none'}
  Action:  {'⚡ YES' if a.get('action_required') else 'no'}""")
    return out

def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <file|url|text>"); sys.exit(1)
    for inp in sys.argv[1:]:
        try: process(inp.strip())
        except Exception as e:
            import traceback; print(f"\n✗ {e}"); traceback.print_exc()

if __name__ == "__main__":
    main()
