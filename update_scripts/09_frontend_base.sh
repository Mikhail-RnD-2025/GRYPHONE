#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 09: ФРОНТЕНД-БАЗА
#  ------------------------------------------------------------
#  Заполняет базовые файлы фронтенда (обязательная часть):
#    - frontend/index.html      — точка входа
#    - frontend/package.json    — зависимости
#    - frontend/vite.config.js  — конфиг Vite с прокси на бэкенд
#
#  Запуск:   bash 09_frontend_base.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# frontend/index.html — точка входа
# ============================================================
cat > "$PROJECT_DIR/frontend/index.html" << 'HTMLEOF'
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GRYPHONE — видеонаблюдение</title>
</head>
<body>
  <!-- Корневой элемент, куда React монтирует всё приложение -->
  <div id="root"></div>
  <!-- Точка входа: скрипт загружает и запускает приложение -->
  <script type="module" src="/src/main.jsx"></script>
</body>
</html>
HTMLEOF
echo "  ✔ frontend/index.html"

# ============================================================
# frontend/package.json — зависимости
# ============================================================
cat > "$PROJECT_DIR/frontend/package.json" << 'JSONEOF'
{
  "name": "gryphone-frontend",
  "version": "0.1.0",
  "description": "Фронтенд системы видеонаблюдения (обязательная часть)",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "hls.js": "^1.4.12"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0"
  }
}
JSONEOF
echo "  ✔ frontend/package.json"

# ============================================================
# frontend/vite.config.js — конфиг Vite с прокси на бэкенд
# ============================================================
cat > "$PROJECT_DIR/frontend/vite.config.js" << 'JSEOF'
// ============================================================
//  GRYPHONE — конфиг фронтенда
//  ------------------------------------------------------------
//  Настраивает сборку и проксирование запросов на бэкенд.
//  В режиме разработки фронтенд запускается на порту 5173,
//  а запросы /api/* и /hls/* перенаправляются на бэкенд :5000.
// ============================================================
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // Подключаем плагин для поддержки синтаксиса библиотеки.
  plugins: [react()],
  // Сервер для режима разработки.
  server: {
    port: 5173,
    // Проксируем запросы на бэкенд, чтобы избежать проблем с
    // одинаковым источником в режиме разработки.
    proxy: {
      // Запросы к прикладному интерфейсу.
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      // Запросы к сегментам потоков.
      '/hls': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
JSEOF
echo "  ✔ frontend/vite.config.js"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in frontend/index.html frontend/package.json frontend/vite.config.js; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo "✅ Фронтенд-база готова (с правильным синтаксисом)."
echo "ℹ️  Ядро фронтенда (точка входа, приложение, стили) — скрипт 10."