#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 10: ЯДРО ФРОНТЕНДА
#  ------------------------------------------------------------
#  Заполняет:
#    - frontend/src/main.jsx               — точка входа
#    - frontend/src/App.jsx                — приложение (роутинг)
#    - frontend/src/styles.css             — стили
#    - frontend/src/api.js                 — клиент прикладного интерфейса
#    - frontend/src/hooks/useStreamStatus.js — хук событий в реальном времени
#
#  Запуск:   bash 10_frontend_core.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# frontend/src/main.jsx — точка входа
# ============================================================
cat > "$PROJECT_DIR/frontend/src/main.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — точка входа фронтенда
//  ------------------------------------------------------------
//  Загружает и запускает приложение, монтируя его в корневой
//  элемент на странице.
// ============================================================
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles.css'

// Находим корневой элемент и создаём точку монтирования.
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
JSXEOF
echo "  ✔ frontend/src/main.jsx"

# ============================================================
# frontend/src/App.jsx — приложение (роутинг)
# ============================================================
cat > "$PROJECT_DIR/frontend/src/App.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — главный компонент приложения
//  ------------------------------------------------------------
//  Определяет роутинг между страницами мониторинга и настроек.
// ============================================================
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import MonitorPage from './pages/MonitorPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Страница мониторинга (главная) */}
        <Route path="/" element={<MonitorPage />} />
        {/* Страница настроек */}
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </BrowserRouter>
  )
}
JSXEOF
echo "  ✔ frontend/src/App.jsx"

# ============================================================
# frontend/src/styles.css — стили
# ============================================================
cat > "$PROJECT_DIR/frontend/src/styles.css" << 'CSSEOF'
/* ============================================================
   GRYPHONE — стили приложения
   ------------------------------------------------------------
   Базовые стили для страниц мониторинга и настроек.
   ============================================================ */

/* Сброс отступов и базовые настройки */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #0b0d10;
  color: #e0e3e8;
  min-height: 100vh;
}

/* Контейнер страницы */
.page {
  padding: 16px;
  max-width: 1200px;
  margin: 0 auto;
}

/* Заголовок страницы */
.page-title {
  font-size: 1.5rem;
  margin-bottom: 16px;
}

/* Сетка камер */
.camera-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

/* Карточка камеры */
.camera-card {
  background: #1e293b;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #334155;
}

/* Статус камеры */
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
}
.status-online {
  background: #059669;
  color: #fff;
}
.status-offline {
  background: #dc2626;
  color: #fff;
}
.status-connecting {
  background: #d97706;
  color: #fff;
}

/* Кнопки */
.btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
}
.btn-primary:hover {
  background: #1d4ed8;
}
.btn-danger {
  background: #dc2626;
  color: #fff;
}
.btn-danger:hover {
  background: #b91c1c;
}

/* Уведомления */
.toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.toast {
  padding: 12px 16px;
  border-radius: 6px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
.toast-success {
  background: #059669;
}
.toast-error {
  background: #dc2626;
}
.toast-info {
  background: #2563eb;
}
CSSEOF
echo "  ✔ frontend/src/styles.css"

# ============================================================
# frontend/src/api.js — клиент прикладного интерфейса
# ============================================================
cat > "$PROJECT_DIR/frontend/src/api.js" << 'JSEOF'
// ============================================================
//  GRYPHONE — клиент прикладного интерфейса
//  ------------------------------------------------------------
//  Обёртки над запросами к бэкенду. Все запросы идут через
//  прокси, настроенный в конфиге сборки.
// ============================================================

// Базовый адрес прикладного интерфейса.
const API_BASE = '/api'

// Универсальная обёртка для запросов.
async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`Ошибка запроса: ${response.status}`)
  }
  return response.json()
}

// ------------------------------------------------------------------
// Камеры
// ------------------------------------------------------------------
export function getCameras() {
  return request('/cameras')
}

export function saveCameras(cameras) {
  return request('/cameras/save', {
    method: 'POST',
    body: JSON.stringify({ cameras }),
  })
}

export function toggleCamera(camId, enabled) {
  return request('/cameras/toggle', {
    method: 'POST',
    body: JSON.stringify({ cam_id: camId, enabled }),
  })
}

export function updateComment(camId, comment) {
  return request('/cameras/comment', {
    method: 'POST',
    body: JSON.stringify({ cam_id: camId, comment }),
  })
}

// ------------------------------------------------------------------
// Наборы
// ------------------------------------------------------------------
export function getSets() {
  return request('/sets')
}

export function saveSets(data) {
  return request('/sets/save', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function switchSet(setId) {
  return request('/sets/switch', {
    method: 'POST',
    body: JSON.stringify({ set_id: setId }),
  })
}

// ------------------------------------------------------------------
// Конфигурация
// ------------------------------------------------------------------
export function getConfig() {
  return request('/config')
}

export function saveConfig(data) {
  return request('/config/save', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ------------------------------------------------------------------
// События
// ------------------------------------------------------------------
export function getEvents() {
  return request('/events')
}

export function publishEvent(event) {
  return request('/events/publish', {
    method: 'POST',
    body: JSON.stringify(event),
  })
}

// ------------------------------------------------------------------
// Дашборд
// ------------------------------------------------------------------
export function getDashboard() {
  return request('/dashboard')
}

// ------------------------------------------------------------------
// Логи
// ------------------------------------------------------------------
export function getFfmpegLogs() {
  return request('/ffmpeg_logs')
}
JSEOF
echo "  ✔ frontend/src/api.js"

# ============================================================
# frontend/src/hooks/useStreamStatus.js — хук событий в реальном времени
# ============================================================
cat > "$PROJECT_DIR/frontend/src/hooks/useStreamStatus.js" << 'JSEOF'
// ============================================================
//  GRYPHONE — хук событий в реальном времени
//  ------------------------------------------------------------
//  Подписывается на поток статусов от бэкенда и возвращает
//  текущие статусы всех потоков.
// ============================================================
import { useState, useEffect } from 'react'

export default function useStreamStatus() {
  // Состояние: статусы всех потоков.
  const [stats, setStats] = useState({})

  useEffect(() => {
    // Создаём подписку на поток событий.
    const source = new EventSource('/api/stream_status')

    // При получении данных обновляем состояние.
    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setStats(data)
      } catch (e) {
        console.error('Ошибка разбора данных:', e)
      }
    }

    // При ошибке логируем (подписка автоматически переподключится).
    source.onerror = () => {
      console.warn('Ошибка подписки на события')
    }

    // При размонтировании компонента закрываем подписку.
    return () => {
      source.close()
    }
  }, [])

  return stats
}
JSEOF
echo "  ✔ frontend/src/hooks/useStreamStatus.js"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in frontend/src/main.jsx frontend/src/App.jsx frontend/src/styles.css frontend/src/api.js frontend/src/hooks/useStreamStatus.js; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo "✅ Ядро фронтенда готово (с правильным синтаксисом)."
echo "ℹ️  Компоненты фронтенда — скрипт 11."