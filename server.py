#!/usr/bin/env python3
"""
Pipeline Server — iPhone connects here via HTTP
No SSH needed. Just POST from Shortcuts.
"""

import os, base64, tempfile, subprocess
from pathlib import Path
from flask import Flask, request, jsonify
from pipeline import process, ensure_vault, VAULT, FOLDERS

app = Flask(__name__)

# ── Health ────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    notes = list(VAULT.rglob("*.md"))
    folders = {k: len(list((VAULT/v).glob("*.md"))) for k,v in FOLDERS.items() if (VAULT/v).exists()}
    return jsonify({"status": "✓ running", "total_notes": len(notes), "breakdown": folders})

# ── Capture anything ──────────────────────────
@app.route("/capture", methods=["POST"])
def capture():
    data = request.get_json(silent=True) or {}

    try:
        # Text or URL
        if "text" in data:
            out = process(data["text"])
            return jsonify({"ok": True, "saved": out.name, "folder": out.parent.name})

        # Image (base64)
        elif "image" in data:
            ext = data.get("ext", "jpg")
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
                f.write(base64.b64decode(data["image"]))
                tmp = f.name
            out = process(tmp)
            os.unlink(tmp)
            return jsonify({"ok": True, "saved": out.name, "folder": out.parent.name})

        # Audio (base64)
        elif "audio" in data:
            ext = data.get("ext", "m4a")
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
                f.write(base64.b64decode(data["audio"]))
                tmp = f.name
            out = process(tmp)
            os.unlink(tmp)
            return jsonify({"ok": True, "saved": out.name, "folder": out.parent.name})

        # Any file (base64)
        elif "file" in data:
            ext = data.get("ext", "pdf")
            name = data.get("name", f"file.{ext}")
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
                f.write(base64.b64decode(data["file"]))
                tmp = f.name
            out = process(tmp)
            os.unlink(tmp)
            return jsonify({"ok": True, "saved": out.name, "folder": out.parent.name})

        else:
            return jsonify({"ok": False, "error": "No input"}), 400

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── Weekly review ─────────────────────────────
@app.route("/review", methods=["GET"])
def review():
    try:
        result = subprocess.run(["python3", "review.py", "week"],
                                capture_output=True, text=True, timeout=60)
        return jsonify({"ok": True, "output": result.stdout[-500:]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── Inbox list ────────────────────────────────
@app.route("/inbox", methods=["GET"])
def inbox():
    d = VAULT / "00-Inbox"
    notes = [f.name for f in sorted(d.glob("*.md"), reverse=True)[:10]] if d.exists() else []
    return jsonify({"count": len(notes), "notes": notes})


if __name__ == "__main__":
    ensure_vault()
    ip = os.popen("hostname -I 2>/dev/null").read().strip().split()
    local_ip = ip[0] if ip else "localhost"
    print(f"""
╔══════════════════════════════════════╗
║      Pipeline Server — RUNNING       ║
╠══════════════════════════════════════╣
║  iPhone URL:                         ║
║  http://{local_ip}:5000        ║
╠══════════════════════════════════════╣
║  Endpoints:                          ║
║  GET  /        — vault status        ║
║  POST /capture — send anything       ║
║  GET  /inbox   — inbox list          ║
║  GET  /review  — weekly review       ║
╚══════════════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=5000, debug=False)
