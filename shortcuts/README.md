# iPhone Shortcuts Setup

6 shortcuts for capturing anything into the pipeline from iPhone.

## How it works

Each Shortcut sends input to a server running pipeline.py via SSH or webhook.
Simplest setup: use **a-Shell** or **iSH** on iPhone, or SSH to Chromebook.

---

## Shortcut 1 — Quick Text / Thought

**Trigger:** Share Sheet or home screen tap

Steps in Shortcuts app:
1. `Ask for Input` — "What's your idea?" (Text)
2. `Run Script over SSH` → `python3 ~/pipeline.py "[input]"`
   OR
2. `Text` → append to file in Working Copy → auto-commit

---

## Shortcut 2 — Capture Photo

1. `Take Photo` (or `Select Photo` from library)
2. `Save to Files` → Working Copy / vault / 00-Inbox / photo.jpg
3. `Run Script over SSH` → `python3 ~/pipeline.py ~/vault/00-Inbox/photo.jpg`

---

## Shortcut 3 — Voice Note

1. `Record Audio`
2. `Save to Files` → Working Copy / vault / 00-Inbox / voice.m4a
3. `Run Script over SSH` → `python3 ~/pipeline.py ~/vault/00-Inbox/voice.m4a`

---

## Shortcut 4 — Share Link (Share Sheet)

**Trigger:** Share Sheet from Safari / any app

1. `Get URLs from Input`
2. `Run Script over SSH` → `python3 ~/pipeline.py "[URL]"`

---

## Shortcut 5 — Scan Document / Screenshot

1. `Scan Document` (or screenshot)
2. `Save to Files` → 00-Inbox
3. `Run Script over SSH` → pipeline.py on the file

---

## Shortcut 6 — Export to NotebookLM

1. `Run Script over SSH`:
   `python3 ~/notebooklm_sync.py`
2. Files appear in ~/notebooklm-sources/
3. Upload to notebooklm.google.com

---

## SSH Setup (Chromebook as server)

```bash
# On Chromebook — enable SSH
sudo apt install openssh-server
sudo systemctl enable ssh
sudo systemctl start ssh

# Get Chromebook local IP
hostname -I
```

In Shortcuts app:
- Host: your Chromebook IP (e.g. 192.168.1.10)
- Port: 22
- User: your username
- Auth: password or SSH key

---

## Alternative: Working Copy only (no SSH)

If no server — use Working Copy to commit files to GitHub,
then pull and process on Chromebook manually:

```bash
# On Chromebook
git -C ~/vault pull
python3 ~/pipeline.py ~/vault/00-Inbox/
```
