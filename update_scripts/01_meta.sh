#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 01: МЕТАФАЙЛЫ
#  ------------------------------------------------------------
#  Заполняет:
#    - requirements.txt   (зависимости Python)
#    - README.md          (описание и запуск)
#    - .gitignore         (для системы контроля версий)
#    - PROD_TODO.md       (⚠️ напоминание о прод-режиме фронтенда)
#
#  Запуск:   bash 01_meta.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ------------------------------------------------------------
# requirements.txt
# ------------------------------------------------------------
cat > "$PROJECT_DIR/requirements.txt" << 'REQEOF'
# GRYPHONE — зависимости бэкенда (Python 3.10+)
flask>=2.3.0
psutil>=5.9.0
REQEOF
echo "  ✔ requirements.txt"

# ------------------------------------------------------------
# .gitignore
# ------------------------------------------------------------
cat > "$PROJECT_DIR/.gitignore" << 'GITEOF'
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/

# Данные и кэш (создаются рантаймом / мигрируются)
*.db
hls_cache/
config.json
cameras.json
sets.json

# Фронтенд (зависимости и прод-сборка)
frontend/node_modules/
frontend/dist/

# IDE
.idea/
.vscode/
GITEOF
echo "  ✔ .gitignore"

# ------------------------------------------------------------
# README.md
# ------------------------------------------------------------
cat > "$PROJECT_DIR/README.md" << 'READMEEOF'
# GRYPHONE — RTSP Viewer

Система видеонаблюдения: просмотрщик потоков + задел под видеорегистратор
и видеоаналитику. Текущая фаза — **стабилизация просмотрщика**.

## Архитектура
- **Бэкенд** (Flask, чистый API): отдаёт `/api/*` и потоки `/hls/*`.
  Ничего не рендерит — серверный HTML-фронтенд удалён.
- **Фронтенд** (React + Vite + hls.js) — обязательная часть.

## Структура