#!/usr/bin/env python3
"""
Pipeline HTTP Server
iPhone sends data here → auto-processes → saves to vault
No SSH needed — simple HTTP from Shortcuts
"""

import os
import json
import base64
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify
from pipeline import process, ensure_vault

app = Flask(__name__)
VAULT = Path(os.environ.get("VAULT_PATH", Path.home() / "vault"))

# ── Health check ──────────────────────────────

@app.route("/", methods=["GET"])
def health():
    notes = list(VAULT.rglob("*.md"))
    return jsonify({
        "status": "running",
        "vault": str(VAULT),
        "notes": len(notes)
    })

# ── Main capture endpoint ──────────────────────

@app.route("/capture", methods=["POST"])
def capture():
    """
    Accepts:
      { "text": "any text or URL" }
      { "image": "<base64>", "ext": "jpg" }
      { "audio": "<base64>", "ext": "m4a" }
      { "file":  "<base64>", "ext": "pdf", "name": "doc.pdf" }
    """
    data = request.get_json(silent=True) or {}

    try:
        if "text" in data:
            out = process(data["text"])
            return jsonify({"ok": True, "saved": out.name})

        elif "image" in data:
            ext = data.get("ext", "jpg")
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
                f.write(base64.b64decode(data["image"]))
                tmp = f.name
            out = process(tmp)
            os.unlink(tmp)
            return jsonify({"ok": True, "saved": out.name})

        elif "audio" in data:
            ext = data.get("ext", "m4a")
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
                f.write(base64.b64decode(data["audio"]))
                tmp = f.name
            out = process(tmp)
            os.unlink(tmp)
            return jsonify({"ok": True, "saved": out.name})

        elif "file" in data:
            ext = data.get("ext", "pdf")
            name = data.get("name", f"file.{ext}")
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
                f.write(base64.b64decode(data["file"]))
                tmp = f.name
            out = process(tmp)
            os.unlink(tmp)
            return jsonify({"ok": True, "saved": out.name})

        else:
            return jsonify({"ok": False, "error": "No input provided"}), 400

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── Inbox list ────────────────────────────────

@app.route("/inbox", methods=["GET"])
def inbox():
    inbox_dir = VAULT / "00-Inbox"
    notes = []
    for md in sorted(inbox_dir.glob("*.md"), reverse=True)[:10]:
        notes.append(md.name)
    return jsonify({"inbox": notes, "count": len(notes)})

# ── Vault stats ───────────────────────────────

@app.route("/stats", methods=["GET"])
def stats():
    folders = {
        "Finance": "01-Finance",
        "AI": "02-AI",
        "Languages": "03-Languages",
        "Projects": "04-Projects",
        "Knowledge": "05-Knowledge",
        "Journal": "06-Journal",
        "Inbox": "00-Inbox",
    }
    counts = {}
    for label, folder in folders.items():
        d = VAULT / folder
        counts[label] = len(list(d.glob("*.md"))) if d.exists() else 0
    return jsonify({"stats": counts, "total": sum(counts.values())})


if __name__ == "__main__":
    ensure_vault()
    local_ip = os.popen("hostname -I").read().strip().split()[0]
    print(f"""
╔══════════════════════════════════════╗
║   Pipeline Server Running            ║
╠══════════════════════════════════════╣
║  Local:   http://localhost:5000      ║
║  iPhone:  http://{local_ip}:5000     ║
╠══════════════════════════════════════╣
║  Endpoints:                          ║
║  POST /capture  — send any content   ║
║  GET  /inbox    — list inbox         ║
║  GET  /stats    — vault statistics   ║
╚══════════════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=5000, debug=False)
