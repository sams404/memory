#!/usr/bin/env python3
"""Weekly & Monthly Review — powered by Gemini"""

import os, re
from datetime import datetime, timedelta
from pathlib import Path
import google.generativeai as genai

VAULT  = Path(os.environ.get("VAULT_PATH", Path.home() / "vault"))
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
client = genai.GenerativeModel("gemini-2.0-flash")

def load_recent(days=7):
    cutoff = datetime.now() - timedelta(days=days)
    notes  = []
    for md in VAULT.rglob("*.md"):
        if md.name == "PROFILE.md": continue
        try:
            if datetime.fromtimestamp(md.stat().st_mtime) >= cutoff:
                notes.append(md.read_text(errors="ignore")[:600])
        except: pass
    return notes

def generate_review(period="week"):
    days  = 7 if period == "week" else 30
    notes = load_recent(days)
    if not notes:
        print("No notes found."); return

    print(f"▶ Analyzing {len(notes)} notes...")
    date = datetime.now().strftime("%Y-%m-%d")

    resp = client.generate_content(f"""Personal growth coach analyzing journal entries.

NOTES FROM LAST {days} DAYS:
{"---".join(notes)[:10000]}

Write a {'weekly' if period == 'week' else 'monthly'} review in markdown:

## Patterns
(recurring themes and behaviors)

## Growth Moments
(wins, breakthroughs, progress)

## Key Lessons
(insights from this period)

## Mood & Energy Trends

## What's Working

## What Needs Attention

## Next {'Week' if period == 'week' else 'Month'} Focus
(1-3 specific priorities)

## One Sentence Summary""")

    folder = VAULT / "06-Reviews"
    folder.mkdir(exist_ok=True)
    out = folder / f"{date}-{period}-review.md"
    out.write_text(f"""---
title: {period.capitalize()} Review — {date}
date: {date}
type: review
period: {period}
notes_analyzed: {len(notes)}
---

{resp.text}
""")
    print(f"\n✓ Saved: {out.name}\n")
    print(resp.text)

if __name__ == "__main__":
    import sys
    generate_review(sys.argv[1] if len(sys.argv) > 1 else "week")
