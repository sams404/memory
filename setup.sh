#!/bin/bash
# ═══════════════════════════════════════════════
# Auto Setup — Obsidian AI Pipeline
# Запусти один раз: bash setup.sh
# ═══════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════"
echo "  Obsidian AI Pipeline — Auto Setup"
echo "═══════════════════════════════════════"

# ── Пути ──────────────────────────────────────
VAULT="$HOME/vault"
PIPELINE_DIR="$HOME/obsidian-ai-pipeline"
ENV_FILE="$HOME/.pipeline_env"

# ── Создать vault структуру ───────────────────
echo ""
echo "▶ Creating vault structure..."
mkdir -p "$VAULT"/{00-Inbox,01-Finance,02-AI,03-Languages,04-Projects,05-Knowledge,06-Journal}
echo "  ✓ Vault: $VAULT"

# ── Установить зависимости ────────────────────
echo ""
echo "▶ Installing dependencies..."
pip install -q anthropic pdfplumber pypdf flask 2>/dev/null || \
pip3 install -q anthropic pdfplumber pypdf flask
echo "  ✓ Python packages installed"

# ── Whisper (опционально, большой) ───────────
read -p "  Install Whisper for audio transcription? (y/n): " WHISPER
if [[ "$WHISPER" == "y" ]]; then
    pip install -q openai-whisper
    echo "  ✓ Whisper installed"
fi

# ── API ключ ──────────────────────────────────
echo ""
echo "▶ Configuration"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    read -p "  Anthropic API key (sk-ant-...): " ANTHROPIC_API_KEY
fi

# ── Сохранить env ─────────────────────────────
cat > "$ENV_FILE" << EOF
export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
export VAULT_PATH="$VAULT"
export PIPELINE_DIR="$PIPELINE_DIR"
export EXPORT_PATH="$HOME/notebooklm-sources"
EOF

# Добавить в bashrc если нет
if ! grep -q "pipeline_env" "$HOME/.bashrc" 2>/dev/null; then
    echo "source $ENV_FILE" >> "$HOME/.bashrc"
fi
echo "  ✓ Environment saved to $ENV_FILE"

# ── Git init vault ────────────────────────────
echo ""
echo "▶ Setting up vault git sync..."
cd "$VAULT"
if [ ! -d ".git" ]; then
    git init
    echo "# Obsidian Vault" > README.md
    echo ".obsidian/workspace" >> .gitignore
    echo ".obsidian/cache" >> .gitignore
    git add .
    git commit -m "init vault"
    echo "  ✓ Vault git initialized"
else
    echo "  ✓ Git already initialized"
fi

# ── Obsidian конфиг (граф + плагины) ──────────
echo ""
echo "▶ Configuring Obsidian..."
mkdir -p "$VAULT/.obsidian"

# Основные настройки
cat > "$VAULT/.obsidian/app.json" << 'EOF'
{
  "defaultViewMode": "source",
  "foldIndent": true,
  "showLineNumber": true,
  "strictLineBreaks": false,
  "showFrontmatter": true
}
EOF

# Настройки графа — цвета по папкам
cat > "$VAULT/.obsidian/graph.json" << 'EOF'
{
  "collapse-filter": false,
  "search": "",
  "showTags": true,
  "showAttachments": false,
  "hideUnresolved": false,
  "showOrphans": true,
  "collapse-color-groups": false,
  "colorGroups": [
    {"query": "path:01-Finance", "color": {"a": 1, "rgb": 14177041}},
    {"query": "path:02-AI",      "color": {"a": 1, "rgb": 5614422}},
    {"query": "path:03-Languages","color": {"a": 1, "rgb": 16744272}},
    {"query": "path:04-Projects", "color": {"a": 1, "rgb": 9699539}},
    {"query": "path:05-Knowledge","color": {"a": 1, "rgb": 6737151}},
    {"query": "path:06-Journal",  "color": {"a": 1, "rgb": 16753920}}
  ],
  "collapse-display": false,
  "showArrow": true,
  "textFadeMultiplier": 0,
  "nodeSizeMultiplier": 1.5,
  "lineSizeMultiplier": 1,
  "scale": 1,
  "close": false
}
EOF
echo "  ✓ Obsidian graph configured with category colors"

# ── Запустить сервер как systemd сервис ───────
echo ""
echo "▶ Setting up auto-start server..."

SERVER_SCRIPT="$PIPELINE_DIR/server.py"

# Создать systemd unit
cat > "$HOME/.config/systemd/user/pipeline.service" << EOF
[Unit]
Description=Obsidian AI Pipeline Server
After=network.target

[Service]
ExecStart=$(which python3) $SERVER_SCRIPT
WorkingDirectory=$PIPELINE_DIR
EnvironmentFile=$ENV_FILE
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

mkdir -p "$HOME/.config/systemd/user"
systemctl --user enable pipeline.service 2>/dev/null && \
systemctl --user start pipeline.service 2>/dev/null && \
echo "  ✓ Server will auto-start on boot" || \
echo "  ℹ Run manually: python3 $SERVER_SCRIPT"

# ── Получить IP ───────────────────────────────
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "═══════════════════════════════════════"
echo "  ✓ Setup Complete!"
echo "═══════════════════════════════════════"
echo ""
echo "  Vault:       $VAULT"
echo "  Server:      http://$LOCAL_IP:5000"
echo ""
echo "  iPhone Shortcuts URL:"
echo "  http://$LOCAL_IP:5000/capture"
echo ""
echo "  Next: open Obsidian → Open folder → $VAULT"
echo "═══════════════════════════════════════"
