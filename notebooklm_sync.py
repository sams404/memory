#!/usr/bin/env python3
"""
NotebookLM Sync Helper
Exports vault notes as formatted sources for NotebookLM upload.
NotebookLM has no public API — this prepares files for manual/Drive upload.
"""

import os
import re
from pathlib import Path
from datetime import datetime

VAULT_PATH  = Path(os.environ.get("VAULT_PATH", Path.home() / "vault"))
EXPORT_PATH = Path(os.environ.get("EXPORT_PATH", Path.home() / "notebooklm-sources"))

FOLDER_MAP = {
    "01-Finance":   "Finance",
    "02-AI":        "AI",
    "03-Languages": "Languages",
    "04-Projects":  "Projects",
    "05-Knowledge": "Knowledge",
}

def export_for_notebooklm(category: str = None):
    """
    Export vault notes as clean text files for NotebookLM.
    Groups by category into single merged documents — easier to upload.
    """
    EXPORT_PATH.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")

    folders = {category: FOLDER_MAP[category]} if category and category in FOLDER_MAP else FOLDER_MAP

    for folder, label in folders.items():
        source_dir = VAULT_PATH / folder
        if not source_dir.exists():
            continue

        notes = list(source_dir.glob("*.md"))
        if not notes:
            continue

        # Merge all notes in category into one document
        merged = f"# {label} Knowledge Base\nExported: {date}\n\n"
        merged += "=" * 60 + "\n\n"

        for note_path in sorted(notes, reverse=True):
            content = note_path.read_text(errors="ignore")

            # strip frontmatter
            content = re.sub(r"^---.*?---\s*", "", content, flags=re.DOTALL)

            # get title from filename
            title = note_path.stem.replace("-", " ").title()
            merged += f"## {title}\n{content.strip()}\n\n"
            merged += "-" * 40 + "\n\n"

        out = EXPORT_PATH / f"{date}-{label.lower()}.txt"
        out.write_text(merged)
        print(f"✓ Exported {len(notes)} notes → {out.name}")

    print(f"\nFiles ready in: {EXPORT_PATH}")
    print("Upload to NotebookLM: notebooklm.google.com → New notebook → Upload sources")


def export_action_items():
    """Export only action-required notes across all categories."""
    EXPORT_PATH.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")

    action_notes = []
    for md in VAULT_PATH.rglob("*.md"):
        content = md.read_text(errors="ignore")
        if "action_required: true" in content:
            title_m = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
            insight_m = re.search(r"## Key Insight\n(.+)", content)
            title = title_m.group(1).strip() if title_m else md.stem
            insight = insight_m.group(1).strip() if insight_m else ""
            action_notes.append(f"### {title}\n{insight}\nFile: {md.name}\n")

    if not action_notes:
        print("No action-required notes found.")
        return

    merged = f"# Action Required — {date}\n\n" + "\n".join(action_notes)
    out = EXPORT_PATH / f"{date}-action-required.txt"
    out.write_text(merged)
    print(f"✓ {len(action_notes)} action items → {out.name}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "actions":
            export_action_items()
        else:
            export_for_notebooklm(sys.argv[1])
    else:
        export_for_notebooklm()
