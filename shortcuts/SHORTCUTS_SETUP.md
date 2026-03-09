# iPhone Shortcuts — Пошаговая настройка

## Подготовка
1. Узнай IP Chromebook: запусти `hostname -I` → скопируй первый IP (напр. `192.168.1.10`)
2. Запусти сервер на Chromebook: `bash ~/obsidian-ai-pipeline/start.sh`
3. Проверь в браузере iPhone: `http://192.168.1.10:5000` — должен ответить статус

---

## Shortcut 1 — 💭 Мысль / Идея

**Shortcuts app → + → Add Action:**

1. `Ask for Input`
   - Prompt: "Мысль, идея или ссылка?"
   - Input Type: Text

2. `Get Contents of URL`
   - URL: `http://ТВОЙ_IP:5000/capture`
   - Method: POST
   - Request Body: JSON
   - Body: `{"text": "[Provided Input]"}`

3. `Get Value for Key` → key: `saved`

4. `Show Notification`
   - Title: "✓ Сохранено"
   - Body: [значение из шага 3]

**Название:** 💭 Capture Thought
**Иконка:** bubble.left
**Добавить на Home Screen**

---

## Shortcut 2 — 📷 Фото

1. `Take Photo` (или `Select Photo`)

2. `Encode Media` → Base64

3. `Get Contents of URL`
   - URL: `http://ТВОЙ_IP:5000/capture`
   - Method: POST
   - Body JSON: `{"image": "[encoded]", "ext": "jpg"}`

4. `Show Notification` → "📷 Фото обработано"

**Название:** 📷 Capture Photo

---

## Shortcut 3 — 🎤 Голос

1. `Record Audio`

2. `Encode Media` → Base64

3. `Get Contents of URL`
   - URL: `http://ТВОЙ_IP:5000/capture`
   - Method: POST
   - Body JSON: `{"audio": "[encoded]", "ext": "m4a"}`

4. `Show Notification` → "🎤 Голос обработан"

**Название:** 🎤 Voice Note

---

## Shortcut 4 — 🔗 Ссылка (Share Sheet)

**Trigger: Share Sheet**

1. `Get URLs from Input`

2. `Get Contents of URL`
   - URL: `http://ТВОЙ_IP:5000/capture`
   - Method: POST
   - Body JSON: `{"text": "[URLs]"}`

3. `Show Notification` → "🔗 Ссылка сохранена"

**Название:** 🔗 Save Link
**Включить в Share Sheet**

---

## Shortcut 5 — 📊 Статус vault

1. `Get Contents of URL`
   - URL: `http://ТВОЙ_IP:5000`
   - Method: GET

2. `Show Result` → показывает количество заметок

**Название:** 📊 Vault Status

---

## Shortcut 6 — 📋 Недельный обзор

1. `Get Contents of URL`
   - URL: `http://ТВОЙ_IP:5000/review`
   - Method: GET

2. `Show Result`

**Название:** 📋 Weekly Review

---

## Виджеты на Home Screen
Добавь Shortcuts виджет → выбери 💭 Capture Thought как главный.
Одно нажатие → мысль в vault.
