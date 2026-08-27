#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 21: ИСПРАВЛЕНИЕ ОСТАВШИХСЯ ОШИБОК ФРОНТА
#  ------------------------------------------------------------
#  Исправляет:
#    1. App.jsx           — добавлен роут * (обработка 404)
#    2. Header.jsx        — выпадающий список для переключения наборов
#    3. ContextMenu.jsx   — закрытие по клику вне меню + проверка границ
#    4. Toasts.jsx        — уникальные id через счётчик
#    5. useStreamStatus.js — обработка ошибок соединения
#    6. styles.css        — стили для выпадающего списка наборов
#
#  Запуск:   bash 21_frontend_fixes.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. frontend/src/App.jsx — добавлена обработка 404
# ============================================================
cat > "$PROJECT_DIR/frontend/src/App.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — главный компонент приложения
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО: добавлен роут * для обработки несуществующих путей.
//  Пользователь перенаправляется на главную страницу.
// ============================================================
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
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
        {/* ИСПРАВЛЕНО: обработка 404 — редирект на главную */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
JSXEOF
echo "  ✔ frontend/src/App.jsx (добавлена обработка 404)"

# ============================================================
# 2. frontend/src/components/Header.jsx — переключение наборов
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/Header.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — компонент «Шапка»
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО: добавлен выпадающий список для переключения
//  между наборами камер. При выборе набора страница
//  перезагружается, чтобы отобразить камеры нового набора.
// ============================================================
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getSets, switchSet, getCurrentSetCameras } from '../api'

export default function Header() {
  // Текущее время для отображения в шапке.
  const [time, setTime] = useState(new Date())
  // Список всех наборов.
  const [sets, setSets] = useState({})
  // Идентификатор текущего набора.
  const [currentSetId, setCurrentSetId] = useState('')

  // Обновляем время каждую секунду.
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Загружаем наборы при монтировании.
  useEffect(() => {
    loadSets()
  }, [])

  const loadSets = async () => {
    try {
      const data = await getSets()
      setSets(data.sets || {})
      // Определяем текущий активный набор.
      const current = await getCurrentSetCameras()
      setCurrentSetId(current.set_id || '')
    } catch (e) {
      console.error('Ошибка загрузки наборов:', e)
    }
  }

  // Обработчик переключения набора.
  const handleSetChange = async (e) => {
    const setId = e.target.value
    try {
      await switchSet(setId)
      // Перезагружаем страницу, чтобы обновить камеры.
      window.location.href = '/'
    } catch (err) {
      console.error('Ошибка переключения набора:', err)
    }
  }

  return (
    <header className="header">
      {/* Заголовок приложения */}
      <h1 className="header-title">GRYPHONE</h1>

      {/* ИСПРАВЛЕНО: выпадающий список наборов */}
      {Object.keys(sets).length > 0 && (
        <select
          className="set-selector"
          value={currentSetId}
          onChange={handleSetChange}
          title="Переключить набор камер"
        >
          {Object.entries(sets).map(([id, set]) => (
            <option key={id} value={id}>{set.name}</option>
          ))}
        </select>
      )}

      {/* Часы */}
      <span className="header-clock">
        {time.toLocaleTimeString()}
      </span>

      {/* Кнопка перехода в настройки */}
      <Link to="/settings" className="btn btn-primary">
        Настройки
      </Link>
    </header>
  )
}
JSXEOF
echo "  ✔ frontend/src/components/Header.jsx (переключение наборов)"

# ============================================================
# 3. frontend/src/components/ContextMenu.jsx — закрытие и границы
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/ContextMenu.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — компонент «Контекстное меню»
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО:
//  - Меню закрывается по клику вне его области.
//  - Проверяются границы экрана: меню не выходит за пределы.
//  - Отображается имя камеры в заголовке меню.
// ============================================================
import { useState, useEffect, useRef } from 'react'
import { toggleCamera, updateComment } from '../api'

export default function ContextMenu({ camera, x, y, onClose, onUpdate }) {
  // Состояние для комментария.
  const [comment, setComment] = useState(camera.comment || '')
  // Ссылка на элемент меню (для отслеживания кликов вне его).
  const menuRef = useRef(null)

  // ИСПРАВЛЕНО: закрытие по клику вне меню.
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [onClose])

  // ИСПРАВЛЕНО: проверка границ экрана.
  // Если меню выходит за правый или нижний край — сдвигаем его.
  const menuWidth = 240
  const menuHeight = 320
  const adjustedX = Math.min(x, window.innerWidth - menuWidth)
  const adjustedY = Math.min(y, window.innerHeight - menuHeight)

  // Обработчик включения/выключения камеры.
  const handleToggle = async () => {
    try {
      await toggleCamera(camera.id, !camera.enabled)
      if (onUpdate) onUpdate()
      onClose()
    } catch (e) {
      console.error('Ошибка переключения камеры:', e)
    }
  }

  // Обработчик сохранения комментария.
  const handleSaveComment = async () => {
    try {
      await updateComment(camera.id, comment)
      if (onUpdate) onUpdate()
      onClose()
    } catch (e) {
      console.error('Ошибка сохранения комментария:', e)
    }
  }

  return (
    <div
      ref={menuRef}
      className="context-menu"
      style={{ position: 'fixed', left: adjustedX, top: adjustedY, zIndex: 100 }}
    >
      {/* Заголовок меню: имя камеры */}
      <div style={{
        fontWeight: 'bold', marginBottom: '12px',
        paddingBottom: '8px', borderBottom: '1px solid #334155',
      }}>
        {camera.name}
      </div>

      {/* Кнопка включения/выключения */}
      <button
        className={`btn ${camera.enabled ? 'btn-danger' : 'btn-primary'}`}
        onClick={handleToggle}
      >
        {camera.enabled ? 'Отключить' : 'Включить'}
      </button>

      {/* Поле для комментария */}
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Комментарий..."
        rows={3}
        style={{ marginTop: '8px', width: '100%' }}
      />

      {/* Кнопка сохранения комментария */}
      <button className="btn btn-primary" onClick={handleSaveComment}>
        Сохранить комментарий
      </button>

      {/* Кнопка закрытия меню */}
      <button className="btn" onClick={onClose}>
        Закрыть
      </button>
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/components/ContextMenu.jsx (закрытие + границы)"

# ============================================================
# 4. frontend/src/components/Toasts.jsx — уникальные id
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/Toasts.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — компонент «Уведомления»
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО: уникальные id через счётчик (ранее использовался
//  Date.now(), что могло дать коллизию при быстром создании).
// ============================================================
import { useState, useEffect, useRef } from 'react'

export default function Toasts() {
  // Список активных уведомлений.
  const [toasts, setToasts] = useState([])
  // ИСПРАВЛЕНО: счётчик для уникальных id.
  const counterRef = useRef(0)

  // Функция для добавления уведомления.
  const addToast = (message, type = 'info') => {
    counterRef.current += 1
    const id = counterRef.current
    setToasts((prev) => [...prev, { id, message, type }])
    // Автоматически удаляем уведомление через 4 секунды.
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }

  // Экспортируем функцию добавления уведомлений через глобальную переменную.
  // При размонтировании компонента очищаем её.
  useEffect(() => {
    window.addToast = addToast
    return () => {
      delete window.addToast
    }
  }, [])

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.type}`}>
          {toast.message}
        </div>
      ))}
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/components/Toasts.jsx (уникальные id)"

# ============================================================
# 5. frontend/src/hooks/useStreamStatus.js — обработка ошибок
# ============================================================
cat > "$PROJECT_DIR/frontend/src/hooks/useStreamStatus.js" << 'JSEOF'
// ============================================================
//  GRYPHONE — хук событий в реальном времени
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО: добавлена обработка ошибок соединения.
//  При ошибке выводится предупреждение в консоль.
// ============================================================
import { useState, useEffect } from 'react'

export default function useStreamStatus() {
  // Состояние: статусы всех потоков.
  const [stats, setStats] = useState({})

  useEffect(() => {
    // Создаём подписку на поток событий.
    const source = new EventSource('/api/stream_status')

    // При успешном подключении.
    source.onopen = () => {
      console.info('Подписка на события установлена')
    }

    // При получении данных обновляем состояние.
    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setStats(data)
      } catch (e) {
        console.error('Ошибка разбора данных:', e)
      }
    }

    // ИСПРАВЛЕНО: при ошибке логируем и полагаемся на
    // автоматическое переподключение EventSource.
    source.onerror = () => {
      console.warn('Ошибка подписки на события, переподключение...')
    }

    // При размонтировании компонента закрываем подписку.
    return () => {
      source.close()
    }
  }, [])

  return stats
}
JSEOF
echo "  ✔ frontend/src/hooks/useStreamStatus.js (обработка ошибок)"

# ============================================================
# 6. frontend/src/styles.css — добавлены стили для выпадающего списка
# ============================================================
cat > "$PROJECT_DIR/frontend/src/styles.css" << 'CSSEOF'
/* ============================================================
   GRYPHONE — стили приложения
   ------------------------------------------------------------
   ДОБАВЛЕНО: стили для выпадающего списка наборов (.set-selector).
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
  max-width: 1400px;
  margin: 0 auto;
}

/* Заголовок страницы */
.page-title {
  font-size: 1.5rem;
  margin-bottom: 16px;
}

/* Шапка приложения */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #1e293b;
  gap: 12px;
}

.header-title {
  font-size: 1.25rem;
  color: #2563eb;
}

.header-clock {
  font-size: 0.875rem;
  color: #94a3b8;
}

/* ДОБАВЛЕНО: выпадающий список наборов */
.set-selector {
  background: #1e293b;
  color: #e0e3e8;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.875rem;
  cursor: pointer;
  outline: none;
}
.set-selector:hover {
  border-color: #2563eb;
}
.set-selector:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}

/* Карточка камеры */
.camera-card {
  background: #1e293b;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #334155;
  transition: border-color 0.2s ease;
}

.camera-card:hover {
  border-color: #2563eb;
}

.camera-name {
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Статус камеры */
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  white-space: nowrap;
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
  background: #334155;
  color: #e0e3e8;
  text-decoration: none;
  display: inline-block;
}
.btn:hover {
  background: #475569;
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

/* Контекстное меню */
.context-menu {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  min-width: 220px;
}

.context-menu .btn {
  width: 100%;
  margin-bottom: 8px;
}

.context-menu textarea {
  background: #0b0d10;
  color: #e0e3e8;
  border: 1px solid #334155;
  border-radius: 4px;
  padding: 8px;
  font-size: 0.875rem;
  resize: vertical;
  font-family: inherit;
}

/* Вкладки на странице настроек */
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.tab-content {
  background: #0b0d10;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #1e293b;
}
CSSEOF
echo "  ✔ frontend/src/styles.css (стили для выпадающего списка)"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in frontend/src/App.jsx frontend/src/components/Header.jsx frontend/src/components/ContextMenu.jsx frontend/src/components/Toasts.jsx frontend/src/hooks/useStreamStatus.js frontend/src/styles.css; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Все ошибки фронтенда исправлены"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что исправлено:"
echo "  • App.jsx: роут * — редирект на главную при 404"
echo "  • Header.jsx: выпадающий список для переключения наборов"
echo "  • ContextMenu.jsx: закрытие по клику вне меню + проверка границ"
echo "  • Toasts.jsx: уникальные id через счётчик"
echo "  • useStreamStatus.js: обработка ошибок соединения"
echo "  • styles.css: стили для выпадающего списка наборов"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000"