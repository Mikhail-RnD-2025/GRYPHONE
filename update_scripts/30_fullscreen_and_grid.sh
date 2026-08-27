#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 30: ИСПРАВЛЕНИЕ FULLSCREEN И СЕТКИ
#  ------------------------------------------------------------
#  Что исправляет:
#    1. FullscreenCamera.jsx — стабильный onClose через useRef,
#       устранён самопроизвольный выход из полноэкранного режима
#    2. MonitorPage.jsx — useCallback для коллбэков, сетка на
#       всю доступную высоту
#    3. CameraCard.jsx — кружочек статуса вместо надписи,
#       гибкая карточка с сохранением пропорций
#    4. styles.css — адаптивная сетка, стили кружочков
#    5. Проверка моделей и стрим-менеджера (_main/_sub)
#
#  Запуск:   bash 30_fullscreen_and_grid.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. FullscreenCamera.jsx — исправлен выход из полноэкранного режима
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/FullscreenCamera.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — полноэкранное окно камеры
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v30):
//  • Стабильная ссылка на onClose через useRef — устранён
//    самопроизвольный выход из полноэкранного режима
//  • Эффект fullscreen запускается только один раз
//  • Выход: двойной клик / Esc / кнопка / системный выход
// ============================================================
import { useEffect, useRef, useState, useCallback } from 'react'
import Hls from 'hls.js'

export default function FullscreenCamera({ camera, onClose }) {
  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  const overlayRef = useRef(null)
  const [error, setError] = useState(null)

  // ИСПРАВЛЕНО (v30): стабильная ссылка на onClose через ref.
  // Это предотвращает перезапуск эффекта при каждой перерисовке
  // родительского компонента (которая происходит каждую секунду
  // из-за SSE-обновлений).
  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  const handleClose = useCallback(() => {
    onCloseRef.current()
  }, [])

  // Всегда основной поток в полноэкранном режиме.
  const routeId = `${camera.id}_main`
  const streamUrl = `/hls/camera/${routeId}/index.m3u8`

  // Инициализация плеера.
  useEffect(() => {
    if (!videoRef.current) return
    setError(null)

    if (Hls.isSupported()) {
      const hls = new Hls({
        liveSyncDurationCount: 2,
        liveMaxLatencyDurationCount: 4,
        lowLatencyMode: true,
      })
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

  // ИСПРАВЛЕНО (v30): эффект запускается только один раз при монтировании.
  // Зависимость [handleClose] стабильна, т.к. создана через useCallback.
  useEffect(() => {
    const el = overlayRef.current
    if (!el) return

    let unmounted = false

    const requestFs = async () => {
      try {
        if (el.requestFullscreen) {
          await el.requestFullscreen()
        } else if (el.webkitRequestFullscreen) {
          el.webkitRequestFullscreen()
        } else if (el.mozRequestFullScreen) {
          el.mozRequestFullScreen()
        }
      } catch (e) {
        console.warn('Fullscreen API недоступен:', e)
      }
    }

    // Задержка, чтобы DOM успел отрендериться и браузер принял жест.
    const timer = setTimeout(requestFs, 150)

    // Слушаем системный выход из fullscreen (Esc браузера).
    const handleFsChange = () => {
      const active = document.fullscreenElement ||
                     document.webkitFullscreenElement ||
                     document.mozFullScreenElement
      if (!active && !unmounted) {
        handleClose()
      }
    }
    document.addEventListener('fullscreenchange', handleFsChange)
    document.addEventListener('webkitfullscreenchange', handleFsChange)
    document.addEventListener('mozfullscreenchange', handleFsChange)

    // Esc на случай, если fullscreen не активировался.
    const handleEsc = (e) => {
      if (e.key === 'Escape' && !document.fullscreenElement) {
        handleClose()
      }
    }
    window.addEventListener('keydown', handleEsc)

    return () => {
      unmounted = true
      clearTimeout(timer)
      document.removeEventListener('fullscreenchange', handleFsChange)
      document.removeEventListener('webkitfullscreenchange', handleFsChange)
      document.removeEventListener('mozfullscreenchange', handleFsChange)
      window.removeEventListener('keydown', handleEsc)
      // ИСПРАВЛЕНО: НЕ вызываем exitFullscreen здесь — это было причиной
      // самопроизвольного выхода при перерисовке родителя.
    }
  }, [handleClose])

  // Двойной клик по видео — выход из полноэкранного режима.
  const handleDoubleClick = () => {
    handleClose()
  }

  return (
    <div
      ref={overlayRef}
      className="fullscreen-overlay"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        background: '#000',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Заголовок: имя камеры, локация, бейдж, кнопка выхода */}
      <div className="fullscreen-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', overflow: 'hidden' }}>
          <span style={{ fontWeight: 'bold', fontSize: '1rem', color: '#e0e3e8', whiteSpace: 'nowrap' }}>
            {camera.name}
          </span>
          {camera.location && (
            <span style={{ fontSize: '0.875rem', color: '#94a3b8', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              📍 {camera.location}
            </span>
          )}
          <span style={{
            fontSize: '0.75rem', color: '#94a3b8',
            background: 'rgba(255,255,255,0.1)', padding: '2px 8px',
            borderRadius: '4px', whiteSpace: 'nowrap',
          }}>
            MAIN • {camera.audio ? '🔊' : '🔇'}
          </span>
        </div>

        <button
          className="btn btn-danger"
          onClick={handleClose}
          style={{ padding: '6px 12px', fontSize: '0.875rem' }}
        >
          ✕ Закрыть
        </button>
      </div>

      {/* Видео на весь экран */}
      <div
        className="fullscreen-video-container"
        onDoubleClick={handleDoubleClick}
        style={{
          flex: 1,
          position: 'relative',
          background: '#000',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          cursor: 'pointer',
          minHeight: 0,
        }}
        title="Двойной клик — выход"
      >
        <video
          ref={videoRef}
          muted={false}
          playsInline
          controls={false}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            background: '#000',
          }}
        />

        {error && (
          <div className="fullscreen-error">
            {error}
          </div>
        )}

        {/* Подсказка снизу */}
        <div style={{
          position: 'absolute', bottom: '12px', left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(0, 0, 0, 0.6)',
          color: '#94a3b8', fontSize: '0.75rem',
          padding: '4px 12px', borderRadius: '4px',
          pointerEvents: 'none', whiteSpace: 'nowrap',
        }}>
          Двойной клик или Esc — выход
        </div>
      </div>
    </div>
  )
}
JSXEOF
echo "  ✔ FullscreenCamera.jsx (стабильный onClose, нет самопроизвольного выхода)"

# ============================================================
# 2. MonitorPage.jsx — стабильные коллбэки, сетка на всю высоту
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница мониторинга
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v30):
//  • useCallback для handleFullscreen / handleCloseFullscreen —
//    стабильные ссылки, не вызывают перезапуск эффекта в
//    FullscreenCamera при каждой перерисовке
//  • Сетка занимает всю доступную высоту с сохранением
//    пропорций и разметки из конфига (max_columns, max_rows)
//  • Статусы читаются по ключу _sub (в сетке субпоток)
// ============================================================
import { useState, useEffect, useCallback } from 'react'
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

  const handleContextMenu = useCallback((camera, x, y) => {
    setContextMenu({ camera, x, y })
  }, [])

  const handleCloseContextMenu = useCallback(() => {
    setContextMenu(null)
  }, [])

  // ИСПРАВЛЕНО (v30): useCallback для стабильных ссылок.
  const handleFullscreen = useCallback((camera) => {
    setFullscreenCamera(camera)
  }, [])

  const handleCloseFullscreen = useCallback(() => {
    setFullscreenCamera(null)
  }, [])

  // ИСПРАВЛЕНО (v30): сетка занимает всю доступную высоту.
  const gridStyle = {
    display: 'grid',
    gap: '8px',
    flex: 1,
    minHeight: 0,
    width: '100%',
  }

  if (setData && setData.max_columns > 0) {
    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, 1fr)`
  } else {
    gridStyle.gridTemplateColumns = 'repeat(auto-fill, minmax(280px, 1fr))'
  }

  if (setData && setData.max_rows > 0) {
    gridStyle.gridTemplateRows = `repeat(${setData.max_rows}, 1fr)`
  }

  const hasSets = setData && setData.set_id !== ''

  return (
    <div className="page">
      <Header />

      {hasSets && cameras.length > 0 && (
        <div style={gridStyle}>
          {cameras.map((camera) => {
            // Статус читаем по ключу _sub (в сетке субпоток).
            const hasSub = camera.sub_url && camera.sub_url.trim() !== '' &&
                           camera.sub_url !== camera.main_url
            const routeId = hasSub
              ? `${camera.id}_sub`
              : `${camera.id}_main`
            const status = stats[routeId]?.state || 'подключение'
            return (
              <CameraCard
                key={camera.id}
                camera={camera}
                status={status}
                onContextMenu={handleContextMenu}
                onFullscreen={handleFullscreen}
              />
            )
          })}
        </div>
      )}

      {!hasSets && (
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          background: '#1e293b', borderRadius: '8px',
          border: '1px dashed #334155',
          margin: '40px auto', maxWidth: '500px',
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

      {hasSets && cameras.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          background: '#1e293b', borderRadius: '8px',
          border: '1px dashed #334155',
          margin: '40px auto', maxWidth: '500px',
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
echo "  ✔ MonitorPage.jsx (useCallback, сетка на всю высоту)"

# ============================================================
# 3. CameraCard.jsx — кружочек статуса, гибкая карточка
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/CameraCard.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — карточка камеры (режим сетки)
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v30):
//  • Кружочек статуса вместо текстовой надписи
//  • Гибкая карточка: заполняет ячейку сетки, видео с
//    object-fit: contain сохраняет пропорции
//  • В сетке всегда субпоток (sub), fallback на main
// ============================================================
import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'

export default function CameraCard({ camera, status, onContextMenu, onFullscreen }) {
  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  const [error, setError] = useState(null)

  // В сетке всегда субпоток; если его нет — основной.
  const hasSub = camera.sub_url && camera.sub_url.trim() !== '' &&
                 camera.sub_url !== camera.main_url
  const routeId = hasSub ? `${camera.id}_sub` : `${camera.id}_main`
  const streamUrl = `/hls/camera/${routeId}/index.m3u8`
  const shouldPlay = camera.enabled && status !== 'недоступна'

  useEffect(() => {
    if (!shouldPlay || !videoRef.current) return
    setError(null)

    if (Hls.isSupported()) {
      const hls = new Hls({
        liveSyncDurationCount: 2,
        liveMaxLatencyDurationCount: 4,
        lowLatencyMode: true,
      })
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

  const handleDoubleClick = () => {
    if (onFullscreen) onFullscreen(camera)
  }

  // ИСПРАВЛЕНО (v30): класс кружочка статуса вместо текстовой надписи.
  const getStatusDot = () => {
    if (!camera.enabled) return 'status-dot offline'
    if (status === 'в_сети') return 'status-dot online'
    if (status === 'недоступна') return 'status-dot offline'
    return 'status-dot connecting'
  }

  const statusText = !camera.enabled ? 'Отключена'
    : status === 'в_сети' ? 'Онлайн'
    : status === 'недоступна' ? 'Недоступна'
    : 'Подключение'

  return (
    <div
      className="camera-card"
      onContextMenu={(e) => {
        e.preventDefault()
        if (onContextMenu) onContextMenu(camera, e.clientX, e.clientY)
      }}
      onDoubleClick={handleDoubleClick}
      style={{ cursor: 'pointer' }}
      title={`${camera.name} — ${statusText}. Двойной клик — на весь экран`}
    >
      {/* Шапка карточки: имя + кружочек статуса */}
      <div className="camera-card-header">
        <span className="camera-name" title={camera.name}>{camera.name}</span>
        <span className={getStatusDot()} title={statusText} />
      </div>

      {/* Локация (если есть) */}
      {camera.location && (
        <div className="camera-location" title={camera.location}>
          📍 {camera.location}
        </div>
      )}

      {/* Видео: заполняет всё доступное пространство ячейки */}
      <div className="camera-video-container">
        {camera.enabled && (
          <video
            ref={videoRef}
            muted
            playsInline
          />
        )}

        {/* Иконка аудио (в углу) */}
        {camera.enabled && status === 'в_сети' && (
          <div className="camera-audio-badge">
            {camera.audio ? '🔊' : '🔇'}
          </div>
        )}

        {/* Индикатор типа потока */}
        {camera.enabled && status === 'в_сети' && (
          <div className="camera-stream-badge">
            {hasSub ? 'SUB' : 'MAIN'}
          </div>
        )}

        {/* Ошибка */}
        {error && (
          <div className="camera-overlay-text" style={{ color: '#dc2626' }}>
            {error}
          </div>
        )}

        {/* Отключена */}
        {!camera.enabled && (
          <div className="camera-overlay-text">
            Камера отключена
          </div>
        )}
      </div>
    </div>
  )
}
JSXEOF
echo "  ✔ CameraCard.jsx (кружочек статуса, гибкая карточка)"

# ============================================================
# 4. styles.css — адаптивная сетка, кружочки, гибкие карточки
# ============================================================
cat > "$PROJECT_DIR/frontend/src/styles.css" << 'CSSEOF'
/* ============================================================
   GRYPHONE — стили приложения
   ------------------------------------------------------------
   ИСПРАВЛЕНО (v30):
   • Сетка занимает всю доступную высоту и ширину
   • Карточки растягиваются на свою ячейку
   • Видео с object-fit: contain сохраняет пропорции
   • Кружочки статуса вместо текстовых плашек
   ============================================================ */

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #root {
  height: 100%;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #0b0d10;
  color: #e0e3e8;
  overflow: hidden;
}

/* ИСПРАВЛЕНО (v30): страница занимает всю высоту, без ограничения ширины */
.page {
  padding: 12px;
  max-width: none;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-title {
  font-size: 1.5rem;
  margin-bottom: 16px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #1e293b;
  gap: 12px;
  flex-shrink: 0;
}

.header-title {
  font-size: 1.25rem;
  color: #2563eb;
}

.header-clock {
  font-size: 0.875rem;
  color: #94a3b8;
}

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

/* ИСПРАВЛЕНО (v30): карточка — гибкий контейнер, заполняет ячейку сетки */
.camera-card {
  background: #1e293b;
  border-radius: 8px;
  padding: 8px;
  border: 1px solid #334155;
  transition: border-color 0.2s ease;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  height: 100%;
}

.camera-card:hover {
  border-color: #2563eb;
}

.camera-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.camera-name {
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.camera-location {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
}

/* ИСПРАВЛЕНО (v30): видео-контейнер растягивается на всю ячейку */
.camera-video-container {
  flex: 1;
  min-height: 0;
  position: relative;
  background: #0b0d10;
  border-radius: 4px;
  overflow: hidden;
  margin-top: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.camera-video-container video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #0b0d10;
}

.camera-audio-badge {
  position: absolute;
  bottom: 4px;
  right: 4px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 0.75rem;
  pointer-events: none;
}

.camera-stream-badge {
  position: absolute;
  top: 4px;
  left: 4px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 0.7rem;
  color: #94a3b8;
  pointer-events: none;
}

.camera-overlay-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #94a3b8;
  font-size: 0.875rem;
  text-align: center;
  pointer-events: none;
  white-space: nowrap;
}

/* ИСПРАВЛЕНО (v30): кружочки статуса */
.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.online {
  background: #059669;
  box-shadow: 0 0 6px #059669;
}
.status-dot.offline {
  background: #dc2626;
  box-shadow: 0 0 6px #dc2626;
}
.status-dot.connecting {
  background: #d97706;
  box-shadow: 0 0 6px #d97706;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

/* Устаревшие плашки (оставлены для совместимости) */
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  white-space: nowrap;
}
.status-online { background: #059669; color: #fff; }
.status-offline { background: #dc2626; color: #fff; }
.status-connecting { background: #d97706; color: #fff; }

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
.btn:hover { background: #475569; }
.btn-primary { background: #2563eb; color: #fff; }
.btn-primary:hover { background: #1d4ed8; }
.btn-danger { background: #dc2626; color: #fff; }
.btn-danger:hover { background: #b91c1c; }

.toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 10000;
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
.toast-success { background: #059669; }
.toast-error { background: #dc2626; }
.toast-info { background: #2563eb; }

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
   Полноэкранный режим (v30)
   ============================================================ */

.fullscreen-overlay {
  background: #000;
}

.fullscreen-overlay:fullscreen,
.fullscreen-overlay:-webkit-full-screen,
.fullscreen-overlay:-moz-full-screen,
.fullscreen-overlay:-ms-fullscreen {
  width: 100vw !important;
  height: 100vh !important;
  padding: 0 !important;
  margin: 0 !important;
}

.fullscreen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.8);
  flex-shrink: 0;
  backdrop-filter: blur(8px);
  z-index: 10;
}

.fullscreen-video-container {
  flex: 1;
  position: relative;
  background: #000;
  min-height: 0;
  overflow: hidden;
}

.fullscreen-video-container video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.fullscreen-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #dc2626;
  font-size: 1.25rem;
  text-align: center;
  background: rgba(0, 0, 0, 0.6);
  padding: 16px 24px;
  border-radius: 8px;
}
CSSEOF
echo "  ✔ styles.css (адаптивная сетка, кружочки статуса)"

# ============================================================
# 5. Проверка и исправление моделей (английские _main/_sub)
# ============================================================
cat > "$PROJECT_DIR/app/models.py" << 'PYEOF_MODELS'
# -*- coding: utf-8 -*-
"""
app/models.py
=============
Модели данных приложения.

ПРОВЕРЕНО (v30): route_id используют английские суффиксы _main/_sub.
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Camera:
    """Модель камеры наблюдения."""

    id: str
    name: str
    main_url: str
    sub_url: str = ""
    enabled: bool = True
    comment: str = ""
    audio: bool = True
    location: str = ""

    @property
    def main_route_id(self) -> str:
        """Идентификатор основного потока (английский суффикс)."""
        return f"{self.id}_main"

    @property
    def sub_route_id(self) -> str:
        """Идентификатор субпотока (английский суффикс)."""
        return f"{self.id}_sub"

    @property
    def has_sub_stream(self) -> bool:
        """Проверяет, есть ли отдельный субпоток."""
        return bool(self.sub_url) and self.sub_url.strip() != "" and \
               self.sub_url != self.main_url

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["Camera"]:
        if not isinstance(raw, dict):
            return None
        cam_id = raw.get("id")
        main_url = raw.get("main_url")
        if not cam_id or not main_url:
            return None
        return cls(
            id=str(cam_id).strip(),
            name=str(raw.get("name", cam_id)).strip(),
            main_url=str(main_url).strip(),
            sub_url=str(raw.get("sub_url", "")).strip(),
            enabled=bool(raw.get("enabled", True)),
            comment=str(raw.get("comment", "")).strip(),
            audio=bool(raw.get("audio", True)),
            location=str(raw.get("location", "")).strip(),
        )


@dataclass
class Set:
    """Модель набора камер."""

    id: str
    name: str
    camera_ids: List[str] = field(default_factory=list)
    max_columns: int = 2
    max_rows: int = 0
    aspect_ratio: str = "16:9"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_raw(cls, set_id: str, raw: Dict[str, Any]) -> Optional["Set"]:
        if not isinstance(raw, dict):
            return None
        return cls(
            id=str(set_id).strip(),
            name=str(raw.get("name", set_id)).strip(),
            camera_ids=[str(cid).strip() for cid in raw.get("camera_ids", [])],
            max_columns=int(raw.get("max_columns", 2)),
            max_rows=int(raw.get("max_rows", 0)),
            aspect_ratio=str(raw.get("aspect_ratio", "16:9")).strip(),
        )


@dataclass
class Event:
    """Модель события системы."""

    source: str
    event_type: str
    severity: str = "info"
    camera_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def make(cls, source: str, event_type: str, severity: str = "info",
             camera_id: Optional[str] = None, payload: Optional[Dict] = None):
        import time
        return cls(
            source=source,
            event_type=event_type,
            severity=severity,
            camera_id=camera_id,
            payload=payload or {},
            timestamp=time.time(),
        )
PYEOF_MODELS
echo "  ✔ app/models.py (английские _main/_sub, свойство has_sub_stream)"

# ============================================================
# 6. Проверка стрим-менеджера (воркеры для main и sub)
# ============================================================
cat > "$PROJECT_DIR/app/services/stream_manager.py" << 'PYEOF_SM'
# -*- coding: utf-8 -*-
"""
app/services/stream_manager.py
==============================
Сервис управления асинхронными воркерами захвата потоков.

ПРОВЕРЕНО (v30): воркеры создаются для обоих потоков (main и sub),
если субпоток существует и отличается от основного.
"""
import asyncio
import logging
import threading
from collections import deque
from typing import Dict, List, Optional

from app.models import Camera

logger = logging.getLogger(__name__)


class StreamManager:
    """Управление воркерами захвата и статусами потоков."""

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._tasks: Dict[str, asyncio.Task] = {}
        self._stats: Dict[str, dict] = {}
        self._logs: Dict[str, deque] = {}
        self._lock = threading.RLock()
        self._log_lock = threading.Lock()
        self._started = False
        self._ready_event = threading.Event()

    def start(self) -> None:
        if self._started:
            return
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="StreamManagerLoop"
        )
        self._thread.start()
        self._started = True
        logger.info("⚡ Асинхронный цикл стримера запущен")

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.call_soon(self._ready_event.set)
        self._loop.run_forever()

    def wait_ready(self, timeout: float = 5.0) -> bool:
        return self._ready_event.wait(timeout)

    def stop(self) -> None:
        if not self._started or self._loop is None:
            return
        for task in list(self._tasks.values()):
            self._loop.call_soon_threadsafe(task.cancel)
        self._tasks.clear()
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._started = False
        logger.info("⏹ Асинхронный цикл стримера остановлен")

    def sync(self, cameras: List[Camera]) -> None:
        if not self._started or self._loop is None:
            logger.warning("⚠️ Стример не запущен, синхронизация отложена")
            return
        asyncio.run_coroutine_threadsafe(self._sync(cameras), self._loop)

    async def _sync(self, cameras: List[Camera]) -> None:
        """Синхронизация воркеров со списком камер.

        ПРОВЕРЕНО (v30): создаёт воркеры для обоих потоков:
          - main_route_id — основной поток (всегда)
          - sub_route_id — субпоток (если есть и отличается от main)
        """
        from app.workers.hls_worker import hls_worker

        needed: Dict[str, tuple] = {}
        for cam in cameras:
            if not cam.enabled:
                continue
            # Основной поток — всегда.
            needed[cam.main_route_id] = (cam.main_url, cam.id)
            # Субпоток — если существует и отличается от основного.
            if cam.has_sub_stream:
                needed[cam.sub_route_id] = (cam.sub_url, cam.id)

        with self._lock:
            # Останавливаем воркеры, которых нет в нужном списке.
            for rid in list(self._tasks.keys()):
                if rid not in needed:
                    task = self._tasks.pop(rid)
                    task.cancel()
                    self._stats.pop(rid, None)
                    logger.info("⏹ Остановлен воркер: %s", rid)
            # Запускаем недостающие воркеры.
            for rid, (url, cam_id) in needed.items():
                if rid not in self._tasks:
                    task = self._loop.create_task(
                        hls_worker(url, rid, cam_id, self)
                    )
                    self._tasks[rid] = task
                    logger.info("🚀 Запущен воркер: %s", rid)

    def set_status(self, route_id: str, state: str, msg: str = "",
                   metrics: Optional[dict] = None) -> None:
        with self._lock:
            self._stats[route_id] = {
                "state": state,
                "msg": msg,
                "metrics": metrics or {},
            }

    def get_all_stats(self) -> Dict[str, dict]:
        with self._lock:
            return dict(self._stats)

    def get_status(self, route_id: str) -> Optional[dict]:
        with self._lock:
            return self._stats.get(route_id)

    def add_log(self, route_id: str, line: str, maxlen: int = 500) -> None:
        with self._log_lock:
            if route_id not in self._logs:
                self._logs[route_id] = deque(maxlen=maxlen)
            self._logs[route_id].append(line)

    def clear_log(self, route_id: str) -> None:
        with self._log_lock:
            if route_id in self._logs:
                self._logs[route_id].clear()

    def get_logs(self, limit: int = 100) -> Dict[str, List[str]]:
        with self._log_lock:
            return {
                rid: list(d)[-limit:]
                for rid, d in self._logs.items()
            }

    def cleanup(self, route_id: str) -> None:
        with self._lock:
            self._tasks.pop(route_id, None)
            self._stats.pop(route_id, None)


stream_manager = StreamManager()
PYEOF_SM
echo "  ✔ app/services/stream_manager.py (воркеры для main и sub)"

# ------------------------------------------------------------
# Проверка
# ------------------------------------------------------------
for f in frontend/src/components/FullscreenCamera.jsx frontend/src/pages/MonitorPage.jsx frontend/src/components/CameraCard.jsx frontend/src/styles.css app/models.py app/services/stream_manager.py; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

# Очистка старых папок с русскими суффиксами (если остались)
echo ""
echo "🧹 Очистка старых папок с русскими суффиксами..."
if [ -d "$PROJECT_DIR/hls_cache/camera" ]; then
  rm -rf "$PROJECT_DIR/hls_cache/camera/"*_основной 2>/dev/null || true
  rm -rf "$PROJECT_DIR/hls_cache/camera/"*_дополнительный 2>/dev/null || true
  echo "  ✔ Старые папки удалены"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Все исправления применены"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что исправлено:"
echo "  • Fullscreen: устранён самопроизвольный выход (useRef + useCallback)"
echo "  • Сетка: занимает всю доступную высоту и ширину"
echo "  • Карточки: растягиваются на ячейку, видео с object-fit: contain"
echo "  • Статусы: кружочки вместо надписей (🟢🟡🔴)"
echo "  • Субпоток: корректная логика has_sub_stream в модели"
echo "  • Воркеры: создаются для обоих потоков (main + sub)"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 (Ctrl+Shift+R)"
echo "  4. Двойной клик на камеру → полноэкранный режим (держится)"
echo "  5. Двойной клик по видео → выход"