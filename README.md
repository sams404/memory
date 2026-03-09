# Obsidian AI Pipeline

Universal information filter with Claude AI analysis. Processes any input format and routes to Obsidian vault automatically.

## Supported Inputs

| Format | Processing |
|--------|-----------|
| Photos (jpg, png, gif, webp) | Claude Vision — OCR + analysis |
| Audio (mp3, wav, m4a, ogg) | Whisper transcription → Claude |
| PDF / Books | pdfplumber extraction → Claude |
| Text files (txt, md, csv, json) | Direct Claude analysis |
| URLs / Links | Web fetch → Claude summary |
| Raw text / Thoughts | Direct Claude analysis |

## Vault Structure

```
vault/
├── 00-Inbox/       # Unprocessed / low relevance
├── 01-Finance/     # Investments, signals, watchlist
├── 02-AI/          # AI projects, automation
├── 03-Languages/   # English & Norwegian learning
├── 04-Projects/    # Active projects
├── 05-Knowledge/   # Reference, research
└── 06-Journal/     # Daily notes
```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export VAULT_PATH="/path/to/your/obsidian/vault"
```

## Usage

```bash
# Photo
python pipeline.py screenshot.jpg

# Audio note
python pipeline.py voice_note.m4a

# PDF / book
python pipeline.py book.pdf

# URL
python pipeline.py https://example.com/article

# Raw thought
python pipeline.py "Idea: automate weekly reports with Claude API"

# Multiple inputs at once
python pipeline.py file1.pdf photo.jpg https://example.com
```

## Output

Each input produces an Obsidian note with:

```yaml
---
title: Auto-generated title
date: 2026-03-09
type: finance|ai|language|project|knowledge|journal
tags: [tag1, tag2]
source: /path/or/url
relevance: 8/10
action_required: true
status: new
---

## Summary
- Key point 1
- Key point 2
- Key point 3

## Key Insight
One sentence takeaway.

## Related
[[related-note-1]]
[[related-note-2]]
```

## Claude Agent (CLAUDE.md)

The included `CLAUDE.md` configures a Claude Code agent for interactive vault management with slash commands:

- `/capture <input>` — run full pipeline
- `/inbox` — list unprocessed items
- `/summary finance` — finance signals summary
- `/find <query>` — search vault
- `/think <topic>` — web-augmented analysis

```bash
cd /path/to/vault
claude  # starts the agent
```

## Stack

- **Claude claude-opus-4-6** — classification, vision, analysis (adaptive thinking)
- **Whisper** — audio transcription (local, offline)
- **pdfplumber** — PDF text extraction
- **Python 3.10+**

## Multi-device Sync

Store vault in a GitHub repo and sync across devices:

- **iPhone**: Obsidian + Working Copy (git)
- **Chromebook**: Obsidian Linux + git CLI + this pipeline
- **Any device**: SSH to server running pipeline
