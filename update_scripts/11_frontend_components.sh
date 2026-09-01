#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 11: КОМПОНЕНТЫ ФРОНТЕНДА
#  ------------------------------------------------------------
#  Заполняет:
#    - frontend/src/components/Header.jsx       — шапка
#    - frontend/src/components/CameraCard.jsx   — карточка камеры
#    - frontend/src/components/ContextMenu.jsx  — контекстное меню
#    - frontend/src/components/Toasts.jsx       — уведомления
#
#  Запуск:   bash 11_frontend_components.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# frontend/src/components/Header.jsx — шапка
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/Header.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — компонент «Шапка»
//  ------------------------------------------------------------
//  Отображает заголовок, часы и кнопку перехода в настройки.
// ============================================================
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function Header() {
  // Текущее время для отображения в шапке.
  const [time, setTime] = useState(new Date())

  // Обновляем время каждую секунду.
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <header className="header">
      {/* Заголовок приложения */}
      <h1 className="header-title">GRYPHONE</h1>

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
echo "  ✔ frontend/src/components/Header.jsx"

# ============================================================
# frontend/src/components/CameraCard.jsx — карточка камеры
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/CameraCard.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — компонент «Карточка камеры»
//  ------------------------------------------------------------
//  Отображает одну камеру: видеопоток (через библиотеку
//  воспроизведения), имя, статус и метрики.
// ============================================================
import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'

export default function CameraCard({ camera, status, onContextMenu }) {
  // Ссылка на элемент видео.
  const videoRef = useRef(null)
  // Экземпляр плеера для воспроизведения потока.
  const hlsRef = useRef(null)
  // Флаг: видео воспроизводится.
  const [isPlaying, setIsPlaying] = useState(false)

  // Путь к плейлисту потока.
  const streamUrl = `/hls/camera/${camera.id}_main/index.m3u8`

  // Инициализируем плеер при монтировании компонента.
  useEffect(() => {
    if (!videoRef.current) return

    // Создаём экземпляр плеера, если браузер его поддерживает.
    if (Hls.isSupported()) {
      const hls = new Hls()
      hls.loadSource(streamUrl)
      hls.attachMedia(videoRef.current)
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        videoRef.current.play().catch(() => {})
        setIsPlaying(true)
      })
      hlsRef.current = hls
    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      // Для браузеров с нативной поддержкой формата.
      videoRef.current.src = streamUrl
      videoRef.current.play().catch(() => {})
      setIsPlaying(true)
    }

    // При размонтировании компонента очищаем плеер.
    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy()
      }
    }
  }, [streamUrl])

  // Определяем класс статуса для отображения.
  const statusClass = status === 'в_сети' ? 'status-online'
    : status === 'недоступна' ? 'status-offline'
    : 'status-connecting'

  return (
    <div
      className="camera-card"
      onContextMenu={(e) => {
        e.preventDefault()
        if (onContextMenu) onContextMenu(camera, e.clientX, e.clientY)
      }}
    >
      {/* Имя камеры */}
      <div className="camera-name">{camera.name}</div>

      {/* Статус камеры */}
      <span className={`status-badge ${statusClass}`}>
        {status || 'подключение'}
      </span>

      {/* Видеопоток */}
      <video
        ref={videoRef}
        muted
        playsInline
        style={{ width: '100%', borderRadius: '4px', marginTop: '8px' }}
      />

      {/* Метрики (если есть) */}
      {status === 'в_сети' && (
        <div className="camera-metrics">
          {/* Здесь можно отобразить битрейт, разрешение и т.д. */}
        </div>
      )}
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/components/CameraCard.jsx"

# ============================================================
# frontend/src/components/ContextMenu.jsx — контекстное меню
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/ContextMenu.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — компонент «Контекстное меню»
//  ------------------------------------------------------------
//  Отображает контекстное меню при правом клике на карточке
//  камеры. Позволяет включить/выключить камеру, обновить
//  комментарий и т.д.
// ============================================================
import { useState } from 'react'
import { toggleCamera, updateComment } from '../api'

export default function ContextMenu({ camera, x, y, onClose, onUpdate }) {
  // Состояние для комментария.
  const [comment, setComment] = useState(camera.comment || '')

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
      className="context-menu"
      style={{ position: 'fixed', left: x, top: y, zIndex: 100 }}
    >
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
echo "  ✔ frontend/src/components/ContextMenu.jsx"

# ============================================================
# frontend/src/components/Toasts.jsx — уведомления
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/Toasts.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — компонент «Уведомления»
//  ------------------------------------------------------------
//  Отображает всплывающие уведомления (успех, ошибка, инфо).
//  Уведомления автоматически исчезают через несколько секунд.
// ============================================================
import { useState, useEffect } from 'react'

export default function Toasts() {
  // Список активных уведомлений.
  const [toasts, setToasts] = useState([])

  // Функция для добавления уведомления.
  const addToast = (message, type = 'info') => {
    const id = Date.now()
    setToasts((prev) => [...prev, { id, message, type }])
    // Автоматически удаляем уведомление через 4 секунды.
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }

  // Экспортируем функцию добавления уведомлений (для использования в других компонентах).
  // Здесь можно использовать контекст или события, но для простоты оставим так.
  useEffect(() => {
    window.addToast = addToast
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
echo "  ✔ frontend/src/components/Toasts.jsx"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in frontend/src/components/Header.jsx frontend/src/components/CameraCard.jsx frontend/src/components/ContextMenu.jsx frontend/src/components/Toasts.jsx; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo "✅ Компоненты фронтенда готовы (с правильным синтаксисом)."
echo "ℹ️  Страницы фронтенда — скрипт 12."