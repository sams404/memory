#!/usr/bin/env python3
"""
Weekly & Monthly Review Generator
Analyzes your vault → finds patterns → generates growth insights
"""

import os, re, json
from datetime import datetime, timedelta
from pathlib import Path
import anthropic

VAULT  = Path(os.environ.get("VAULT_PATH", Path.home() / "vault"))
MODEL  = "claude-opus-4-6"
client = anthropic.Anthropic()

def load_recent_notes(days=7):
    cutoff = datetime.now() - timedelta(days=days)
    notes  = []
    for md in VAULT.rglob("*.md"):
        if md.name in ("PROFILE.md",): continue
        try:
            mtime = datetime.fromtimestamp(md.stat().st_mtime)
            if mtime >= cutoff:
                notes.append(md.read_text(errors="ignore")[:800])
        except: pass
    return notes

def generate_review(period="week"):
    days  = 7 if period == "week" else 30
    notes = load_recent_notes(days)
    if not notes:
        print("No notes found for this period."); return

    combined = "\n---\n".join(notes)
    date     = datetime.now().strftime("%Y-%m-%d")

    print(f"▶ Analyzing {len(notes)} notes from last {days} days...")

    with client.messages.stream(
        model=MODEL, max_tokens=2048,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": f"""You are a personal growth coach analyzing someone's journal.

NOTES FROM LAST {days} DAYS:
{combined[:12000]}

Generate a {'weekly' if period == 'week' else 'monthly'} review in markdown:

## Pattern Recognition
(what themes and patterns appear repeatedly)

## Growth Moments
(specific wins, breakthroughs, progress)

## Lessons Learned
(key insights from this period)

## Energy & Mood Trends
(how mood/energy shifted and why)

## What's Working
(habits, approaches giving results)

## What Needs Attention
(blockers, unresolved issues, neglected areas)

## Focus for Next {'Week' if period == 'week' else 'Month'}
(1-3 specific priorities based on patterns)

## One Sentence Summary
(capture the essence of this period)

Be specific, reference actual notes, give real growth insights."""}]
    ) as s:
        review_text = s.get_final_message().content[-1].text

    # Save review
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

{review_text}
""")
    print(f"\n✓ Review saved: {out.name}")
    print("\n" + "="*50)
    print(review_text)

if __name__ == "__main__":
    import sys
    period = sys.argv[1] if len(sys.argv) > 1 else "week"
    generate_review(period)
