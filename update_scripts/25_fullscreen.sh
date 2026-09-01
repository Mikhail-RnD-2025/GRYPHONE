#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 25: ПОЛНОЭКРАННЫЙ РЕЖИМ КАМЕРЫ
#  ------------------------------------------------------------
#  Что делает:
#    1. Создаёт frontend/src/components/FullscreenCamera.jsx
#       — модальное окно с видеоплеером на весь экран
#    2. Обновляет CameraCard.jsx — двойной клик открывает
#       полноэкранное окно (вместо переключения потока)
#    3. Обновляет MonitorPage.jsx — управление модальным окном
#    4. Обновляет ContextMenu.jsx — пункт "На весь экран"
#    5. Обновляет styles.css — стили модального окна
#
#  Запуск:   bash 25_fullscreen.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. FullscreenCamera.jsx — модальное окно с видеоплеером
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/FullscreenCamera.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — полноэкранное окно камеры
//  ------------------------------------------------------------
//  Модальное окно, которое раскрывает камеру на весь экран.
//  Открывается по двойному клику на карточку камеры.
//  Закрывается по клику вне окна, по клавише Esc или кнопкой.
// ============================================================
import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'

export default function FullscreenCamera({ camera, onClose }) {
  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  // Тип потока: 'основной' или 'дополнительный'
  const [streamType, setStreamType] = useState('основной')
  const [error, setError] = useState(null)

  const routeId = `${camera.id}_${streamType}`
  const streamUrl = `/hls/camera/${routeId}/index.m3u8`

  // Создаём плеер при монтировании и при смене типа потока.
  useEffect(() => {
    if (!videoRef.current) return
    setError(null)

    if (Hls.isSupported()) {
      const hls = new Hls()
      hls.loadSource(streamUrl)
      hls.attachMedia(videoRef.current)

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        videoRef.current.play().catch(() => {})
      })

      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          setError('Поток недоступен')
          hls.destroy()
          hlsRef.current = null
        }
      })

      hlsRef.current = hls
    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      videoRef.current.src = streamUrl
      videoRef.current.play().catch(() => setError('Не удалось воспроизвести'))
    }

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
    }
  }, [streamUrl])

  // Закрытие по клавише Esc.
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [onClose])

  // Переключение между потоками.
  const handleSwitchStream = () => {
    if (camera.sub_url && camera.sub_url !== camera.main_url) {
      setStreamType(prev => prev === 'основной' ? 'дополнительный' : 'основной')
    }
  }

  const hasSubStream = camera.sub_url && camera.sub_url !== camera.main_url

  return (
    <div className="fullscreen-overlay" onClick={onClose}>
      <div className="fullscreen-content" onClick={(e) => e.stopPropagation()}>
        {/* Заголовок с именем камеры и кнопками */}
        <div className="fullscreen-header">
          <span style={{ fontWeight: 'bold', fontSize: '1rem' }}>
            {camera.name}
            <span style={{ marginLeft: '12px', fontSize: '0.875rem', color: '#94a3b8' }}>
              {streamType === 'основной' ? 'Основной поток' : 'Дополнительный поток'}
            </span>
          </span>

          <div style={{ display: 'flex', gap: '8px' }}>
            {/* Кнопка переключения потока (если есть субпоток) */}
            {hasSubStream && (
              <button className="btn" onClick={handleSwitchStream}>
                Переключить поток
              </button>
            )}
            {/* Кнопка закрытия */}
            <button className="btn btn-danger" onClick={onClose}>
              Закрыть (Esc)
            </button>
          </div>
        </div>

        {/* Видео на весь экран */}
        <div className="fullscreen-video-container">
          <video
            ref={videoRef}
            muted
            playsInline
            controls={false}
          />

          {/* Сообщение об ошибке */}
          {error && (
            <div className="fullscreen-error">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/components/FullscreenCamera.jsx"

# ============================================================
# 2. CameraCard.jsx — двойной клик открывает полноэкранное окно
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/CameraCard.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — компонент «Карточка камеры»
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v25): двойной клик открывает полноэкранное окно
//  (вместо переключения потока). Переключение потока доступно
//  в контекстном меню и в полноэкранном окне.
// ============================================================
import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'

export default function CameraCard({ camera, status, aspectRatio, onContextMenu, onFullscreen }) {
  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  // Всегда показываем основной поток в сетке (переключение — в полноэкранном окне)
  const [streamType, setStreamType] = useState('основной')
  const [error, setError] = useState(null)

  const routeId = `${camera.id}_${streamType}`
  const streamUrl = `/hls/camera/${routeId}/index.m3u8`

  const shouldPlay = camera.enabled && status !== 'недоступна'

  useEffect(() => {
    if (!shouldPlay || !videoRef.current) return

    setError(null)

    if (Hls.isSupported()) {
      const hls = new Hls()
      hls.loadSource(streamUrl)
      hls.attachMedia(videoRef.current)

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        videoRef.current.play().catch(() => {})
      })

      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          setError('Поток недоступен')
          hls.destroy()
          hlsRef.current = null
        }
      })

      hlsRef.current = hls
    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      videoRef.current.src = streamUrl
      videoRef.current.play().catch(() => setError('Не удалось воспроизвести'))
    }

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
    }
  }, [streamUrl, shouldPlay])

  // ИСПРАВЛЕНО: двойной клик открывает полноэкранное окно.
  const handleDoubleClick = () => {
    if (onFullscreen) {
      onFullscreen(camera)
    }
  }

  const getStatusBadge = () => {
    if (!camera.enabled) return { text: 'Отключена', cls: 'status-offline' }
    if (status === 'в_сети') return { text: 'Онлайн', cls: 'status-online' }
    if (status === 'недоступна') return { text: 'Недоступна', cls: 'status-offline' }
    return { text: 'Подключение', cls: 'status-connecting' }
  }

  const badge = getStatusBadge()
  const aspectStyle = aspectRatio === '4:3' ? '75%' : '56.25%'

  return (
    <div
      className="camera-card"
      onContextMenu={(e) => {
        e.preventDefault()
        if (onContextMenu) onContextMenu(camera, e.clientX, e.clientY)
      }}
      onDoubleClick={handleDoubleClick}
      style={{ cursor: 'pointer' }}
      title="Двойной клик — на весь экран"
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="camera-name">{camera.name}</span>
        <span className={`status-badge ${badge.cls}`}>{badge.text}</span>
      </div>

      <div style={{
        position: 'relative', width: '100%',
        paddingTop: aspectStyle, marginTop: '8px',
        background: '#0b0d10', borderRadius: '4px', overflow: 'hidden',
      }}>
        {camera.enabled && (
          <video
            ref={videoRef}
            muted
            playsInline
            style={{
              position: 'absolute', top: 0, left: 0,
              width: '100%', height: '100%', objectFit: 'contain',
            }}
          />
        )}

        {error && (
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#dc2626', fontSize: '0.875rem', textAlign: 'center',
          }}>
            {error}
          </div>
        )}

        {!camera.enabled && (
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#94a3b8', fontSize: '0.875rem', textAlign: 'center',
          }}>
            Камера отключена
          </div>
        )}
      </div>

      {status === 'в_сети' && (
        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '4px' }}>
          {streamType === 'основной' ? 'Основной поток' : 'Дополнительный поток'}
        </div>
      )}
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/components/CameraCard.jsx (двойной клик → полноэкранное окно)"

# ============================================================
# 3. MonitorPage.jsx — управление модальным окном
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница мониторинга
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v25): добавлено управление полноэкранным окном.
//  Двойной клик на карточку открывает камеру на весь экран.
// ============================================================
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import Header from '../components/Header'
import CameraCard from '../components/CameraCard'
import FullscreenCamera from '../components/FullscreenCamera'
import ContextMenu from '../components/ContextMenu'
import Toasts from '../components/Toasts'
import useStreamStatus from '../hooks/useStreamStatus'
import { getCurrentSetCameras } from '../api'

export default function MonitorPage() {
  const [setData, setSetData] = useState(null)
  const [cameras, setCameras] = useState([])
  const [contextMenu, setContextMenu] = useState(null)
  // ИСПРАВЛЕНО: состояние полноэкранной камеры.
  const [fullscreenCamera, setFullscreenCamera] = useState(null)

  const stats = useStreamStatus()

  useEffect(() => {
    loadCurrentSet()
  }, [])

  const loadCurrentSet = async () => {
    try {
      const data = await getCurrentSetCameras()
      setSetData(data)
      setCameras(data.cameras || [])
    } catch (e) {
      console.error('Ошибка загрузки камер набора:', e)
    }
  }

  const handleContextMenu = (camera, x, y) => {
    setContextMenu({ camera, x, y })
  }

  const handleCloseContextMenu = () => {
    setContextMenu(null)
  }

  // ИСПРАВЛЕНО: открытие полноэкранного окна.
  const handleFullscreen = (camera) => {
    setFullscreenCamera(camera)
  }

  // ИСПРАВЛЕНО: закрытие полноэкранного окна.
  const handleCloseFullscreen = () => {
    setFullscreenCamera(null)
  }

  // Вычисляем стиль сетки на основе настроек набора.
  const gridStyle = {
    display: 'grid',
    gap: '12px',
  }

  if (setData && setData.max_columns > 0) {
    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, 1fr)`
  } else {
    gridStyle.gridTemplateColumns = 'repeat(auto-fill, minmax(300px, 1fr))'
  }

  // Определяем, что показать, если камер нет.
  const hasSets = setData && setData.set_id !== ''

  return (
    <div className="page">
      <Header />

      {/* Информация о наборе (только если набор существует) */}
      {hasSets && (
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: '12px',
        }}>
          <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
            Набор: <strong style={{ color: '#e0e3e8' }}>{setData.set_name}</strong>
            {' '}• Камер: {cameras.length}
          </span>
        </div>
      )}

      {/* Сетка камер (только если набор существует и есть камеры) */}
      {hasSets && cameras.length > 0 && (
        <div style={gridStyle}>
          {cameras.map((camera) => {
            const routeId = camera.id + '_основной'
            const status = stats[routeId]?.state || 'подключение'
            return (
              <CameraCard
                key={camera.id}
                camera={camera}
                status={status}
                aspectRatio={setData?.aspect_ratio || '16:9'}
                onContextMenu={handleContextMenu}
                onFullscreen={handleFullscreen}
              />
            )
          })}
        </div>
      )}

      {/* Сообщение: наборы не созданы */}
      {!hasSets && (
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          background: '#1e293b', borderRadius: '8px',
          border: '1px dashed #334155',
        }}>
          <div style={{ fontSize: '1.25rem', marginBottom: '12px' }}>
            📹 Наборы не созданы
          </div>
          <div style={{ color: '#94a3b8', marginBottom: '20px' }}>
            Для начала работы создайте набор камер и добавьте в него камеры.
          </div>
          <Link to="/settings" className="btn btn-primary">
            Перейти в настройки
          </Link>
        </div>
      )}

      {/* Сообщение: набор существует, но камер в нём нет */}
      {hasSets && cameras.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          background: '#1e293b', borderRadius: '8px',
          border: '1px dashed #334155',
        }}>
          <div style={{ fontSize: '1.25rem', marginBottom: '12px' }}>
            📹 В наборе «{setData.set_name}» нет камер
          </div>
          <div style={{ color: '#94a3b8', marginBottom: '20px' }}>
            Добавьте камеры в этот набор через настройки.
          </div>
          <Link to="/settings" className="btn btn-primary">
            Перейти в настройки
          </Link>
        </div>
      )}

      {/* Контекстное меню */}
      {contextMenu && (
        <ContextMenu
          camera={contextMenu.camera}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={handleCloseContextMenu}
          onUpdate={loadCurrentSet}
          onFullscreen={handleFullscreen}
        />
      )}

      {/* ИСПРАВЛЕНО: полноэкранное окно камеры */}
      {fullscreenCamera && (
        <FullscreenCamera
          camera={fullscreenCamera}
          onClose={handleCloseFullscreen}
        />
      )}

      <Toasts />
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/MonitorPage.jsx (управление полноэкранным окном)"

# ============================================================
# 4. ContextMenu.jsx — добавлен пункт «На весь экран»
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/ContextMenu.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — компонент «Контекстное меню»
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v25): добавлен пункт «На весь экран», который
//  открывает камеру в полноэкранном окне.
// ============================================================
import { useState, useEffect, useRef } from 'react'
import { toggleCamera, updateComment } from '../api'

export default function ContextMenu({ camera, x, y, onClose, onUpdate, onFullscreen }) {
  const [comment, setComment] = useState(camera.comment || '')
  const menuRef = useRef(null)

  // Закрытие по клику вне меню.
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

  // Проверка границ экрана.
  const menuWidth = 240
  const menuHeight = 380
  const adjustedX = Math.min(x, window.innerWidth - menuWidth)
  const adjustedY = Math.min(y, window.innerHeight - menuHeight)

  const handleToggle = async () => {
    try {
      await toggleCamera(camera.id, !camera.enabled)
      if (onUpdate) onUpdate()
      onClose()
    } catch (e) {
      console.error('Ошибка переключения камеры:', e)
    }
  }

  const handleSaveComment = async () => {
    try {
      await updateComment(camera.id, comment)
      if (onUpdate) onUpdate()
      onClose()
    } catch (e) {
      console.error('Ошибка сохранения комментария:', e)
    }
  }

  // ИСПРАВЛЕНО: открытие полноэкранного окна из контекстного меню.
  const handleFullscreen = () => {
    if (onFullscreen) {
      onFullscreen(camera)
    }
    onClose()
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

      {/* ИСПРАВЛЕНО: пункт «На весь экран» */}
      <button className="btn btn-primary" onClick={handleFullscreen}>
        🖥 На весь экран
      </button>

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
echo "  ✔ frontend/src/components/ContextMenu.jsx (пункт «На весь экран»)"

# ============================================================
# 5. styles.css — стили полноэкранного окна
# ============================================================
cat > "$PROJECT_DIR/frontend/src/styles.css" << 'CSSEOF'
/* ============================================================
   GRYPHONE — стили приложения
   ------------------------------------------------------------
   ДОБАВЛЕНО (v25): стили полноэкранного окна камеры.
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

/* Выпадающий список наборов */
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

/* ============================================================
   ДОБАВЛЕНО (v25): Полноэкранное окно камеры
   ============================================================ */

/* Оверлей на весь экран с затемнением */
.fullscreen-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.92);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

/* Контент полноэкранного окна */
.fullscreen-content {
  width: 95vw;
  height: 92vh;
  background: #0b0d10;
  border-radius: 12px;
  border: 1px solid #334155;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
}

/* Заголовок полноэкранного окна */
.fullscreen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #334155;
  background: #1e293b;
  flex-shrink: 0;
}

/* Контейнер видео в полноэкранном окне */
.fullscreen-video-container {
  flex: 1;
  position: relative;
  background: #000;
  min-height: 0;
}

.fullscreen-video-container video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

/* Сообщение об ошибке в полноэкранном окне */
.fullscreen-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #dc2626;
  font-size: 1.25rem;
  text-align: center;
}
CSSEOF
echo "  ✔ frontend/src/styles.css (стили полноэкранного окна)"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in frontend/src/components/FullscreenCamera.jsx frontend/src/components/CameraCard.jsx frontend/src/pages/MonitorPage.jsx frontend/src/components/ContextMenu.jsx frontend/src/styles.css; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Полноэкранный режим реализован"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что изменилось:"
echo "  • Двойной клик на карточку → открывает полноэкранное окно"
echo "  • Правый клик → контекстное меню с пунктом «На весь экран»"
echo "  • Полноэкранное окно закрывается по:"
echo "    - клику вне окна"
echo "    - клавише Esc"
echo "    - кнопке «Закрыть»"
echo "  • Переключение основного/субпотока — в полноэкранном окне"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000"
echo "  4. Двойной клик на камеру → полноэкранное окно"