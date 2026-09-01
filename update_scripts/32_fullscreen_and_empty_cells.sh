#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 32: ЧИСТЫЙ FULLSCREEN + ПУСТЫЕ ЯЧЕЙКИ
#  ------------------------------------------------------------
#  Что меняет:
#    1. Полноэкранный режим:
#       • Убрана красная кнопка «Закрыть»
#       • Убрана шапка — видео на весь экран без отступов
#       • Имя камеры — автоскрываемый оверлей (появляется при
#         движении мыши, исчезает через 3 сек)
#       • Выход: двойной клик / Esc
#    2. Сетка:
#       • Пустые ячейки рендерятся и помечаются отдельным цветом
#       • Стильный значок «объектив» в центре пустой ячейки
#
#  Запуск:   bash 32_fullscreen_and_empty_cells.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. FullscreenCamera.jsx — чистый режим без шапки и кнопки
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/FullscreenCamera.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — полноэкранное окно камеры
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v32):
//  • Убрана шапка и красная кнопка «Закрыть»
//  • Видео на весь экран без отступов (position: fixed, inset: 0)
//  • Имя камеры — автоскрываемый оверлей сверху (появляется при
//    движении мыши, исчезает через 3 секунды)
//  • Выход: двойной клик по видео / Esc / системный выход
// ============================================================
import { useEffect, useRef, useState, useCallback } from 'react'
import Hls from 'hls.js'

export default function FullscreenCamera({ camera, onClose }) {
  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  const overlayRef = useRef(null)
  const hideTimerRef = useRef(null)
  const [error, setError] = useState(null)
  const [showInfo, setShowInfo] = useState(true)

  // Стабильная ссылка на onClose (защита от перерисовок родителя).
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

  // ИСПРАВЛЕНО (v32): автоскрываемый оверлей с именем камеры.
  // Показывается при движении мыши, скрывается через 3 секунды.
  useEffect(() => {
    const showInfoTemporarily = () => {
      setShowInfo(true)
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
      hideTimerRef.current = setTimeout(() => setShowInfo(false), 3000)
    }

    window.addEventListener('mousemove', showInfoTemporarily)
    // Показать сразу при открытии.
    showInfoTemporarily()

    return () => {
      window.removeEventListener('mousemove', showInfoTemporarily)
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
    }
  }, [])

  // Полноэкранный режим + обработка выхода.
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

    const timer = setTimeout(requestFs, 150)

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
    }
  }, [handleClose])

  // Двойной клик — выход.
  const handleDoubleClick = () => {
    handleClose()
  }

  return (
    <div
      ref={overlayRef}
      className="fullscreen-overlay"
      onDoubleClick={handleDoubleClick}
      title="Двойной клик или Esc — выход"
    >
      {/* Видео на весь экран */}
      <video
        ref={videoRef}
        muted={false}
        playsInline
        controls={false}
        className="fullscreen-video"
      />

      {/* Автоскрываемый оверлей с именем камеры */}
      <div className={`fullscreen-info-overlay ${showInfo ? '' : 'hidden'}`}>
        <span className="fullscreen-info-name">{camera.name}</span>
        {camera.location && (
          <span className="fullscreen-info-location">📍 {camera.location}</span>
        )}
        <span className="fullscreen-info-badge">
          MAIN • {camera.audio ? '🔊' : '🔇'}
        </span>
      </div>

      {/* Ошибка */}
      {error && (
        <div className="fullscreen-error">
          {error}
        </div>
      )}
    </div>
  )
}
JSXEOF
echo "  ✔ FullscreenCamera.jsx (чистый экран, автоскрываемый оверлей)"

# ============================================================
# 2. MonitorPage.jsx — пустые ячейки-заглушки в сетке
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница мониторинга
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v32):
//  • Пустые ячейки в сетке рендеруются и помечаются отдельным
//    цветом, чтобы сетка выглядела завершённой
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

  const handleFullscreen = useCallback((camera) => {
    setFullscreenCamera(camera)
  }, [])

  const handleCloseFullscreen = useCallback(() => {
    setFullscreenCamera(null)
  }, [])

  const gridStyle = {
    display: 'grid',
    gap: '2px',
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

  // ИСПРАВЛЕНО (v32): число пустых ячеек для заполнения всей сетки.
  const hasFixedGrid = setData && setData.max_columns > 0 && setData.max_rows > 0
  const totalCells = hasFixedGrid ? setData.max_columns * setData.max_rows : cameras.length
  const emptyCount = Math.max(0, totalCells - cameras.length)

  const hasSets = setData && setData.set_id !== ''

  return (
    <div className="page">
      <Header />

      {hasSets && cameras.length > 0 && (
        <div style={gridStyle}>
          {cameras.map((camera) => {
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

          {/* ИСПРАВЛЕНО (v32): пустые ячейки-заглушки */}
          {Array.from({ length: emptyCount }).map((_, i) => (
            <div key={`empty-${i}`} className="camera-empty" />
          ))}
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
echo "  ✔ MonitorPage.jsx (пустые ячейки-заглушки)"

# ============================================================
# 3. styles.css — чистый fullscreen + стиль пустых ячеек
# ============================================================
cat > "$PROJECT_DIR/frontend/src/styles.css" << 'CSSEOF'
/* ============================================================
   GRYPHONE — стили приложения
   ------------------------------------------------------------
   ИСПРАВЛЕНО (v32):
   • Полноэкранный режим: чистый экран без шапки и кнопки,
     видео на всю площадь без отступов
   • Пустые ячейки: отдельный цвет + значок «объектив»
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

.page {
  padding: 8px;
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
  margin-bottom: 8px;
  padding-bottom: 8px;
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
.set-selector:hover { border-color: #2563eb; }
.set-selector:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}

/* ============================================================
   Ячейка камеры (видеостена)
   ============================================================ */

.camera-card {
  position: relative;
  overflow: hidden;
  background: #000;
  border: none;
  border-radius: 0;
  padding: 0;
  display: flex;
  min-height: 0;
  height: 100%;
}

.camera-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
  z-index: 1;
}

.camera-card-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
  padding: 3px 6px;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.65) 0%,
    rgba(0, 0, 0, 0.25) 70%,
    transparent 100%
  );
  pointer-events: none;
}

.camera-name {
  font-size: 0.7rem;
  font-weight: 500;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 3px rgba(0, 0, 0, 0.5);
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

.camera-audio-badge {
  position: absolute;
  bottom: 4px;
  right: 4px;
  z-index: 2;
  background: rgba(0, 0, 0, 0.55);
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 0.7rem;
  pointer-events: none;
}

.camera-stream-badge {
  position: absolute;
  bottom: 4px;
  left: 4px;
  z-index: 2;
  background: rgba(0, 0, 0, 0.55);
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 0.65rem;
  color: #94a3b8;
  pointer-events: none;
}

.camera-overlay-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  color: #94a3b8;
  font-size: 0.8rem;
  text-align: center;
  pointer-events: none;
  white-space: nowrap;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.9);
}

/* ============================================================
   ИСПРАВЛЕНО (v32): пустая ячейка в сетке
   Отличается от фона, выглядит стильно (значок «объектив»)
   ============================================================ */

.camera-empty {
  position: relative;
  background: linear-gradient(135deg, #0f1116 0%, #13151c 100%);
  border: 1px dashed #24272f;
  border-radius: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  min-height: 0;
  height: 100%;
}

/* Значок «объектив камеры»: кольцо с точкой в центре */
.camera-empty::before {
  content: '';
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1.5px solid #2e313a;
  background: radial-gradient(
    circle,
    #2e313a 0%,
    #2e313a 22%,
    transparent 23%
  );
  opacity: 0.8;
}

/* Устаревшие плашки (для совместимости) */
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
   ИСПРАВЛЕНО (v32): полноэкранный режим — чистый экран
   ============================================================ */

/* Оверлей: без отступов, на весь экран */
.fullscreen-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: #000;
  z-index: 9999;
  overflow: hidden;
  cursor: pointer;
  padding: 0;
  margin: 0;
}

.fullscreen-overlay:fullscreen,
.fullscreen-overlay:-webkit-full-screen,
.fullscreen-overlay:-moz-full-screen,
.fullscreen-overlay:-ms-fullscreen {
  width: 100vw !important;
  height: 100vh !important;
  padding: 0 !important;
  margin: 0 !important;
  top: 0 !important;
  left: 0 !important;
}

/* Видео на всю площадь без отступов */
.fullscreen-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
  z-index: 1;
}

/* Автоскрываемый оверлей с именем камеры */
.fullscreen-info-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 20px;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.7) 0%,
    rgba(0, 0, 0, 0.3) 60%,
    transparent 100%
  );
  pointer-events: none;
  transition: opacity 0.4s ease;
  opacity: 1;
}

.fullscreen-info-overlay.hidden {
  opacity: 0;
}

.fullscreen-info-name {
  font-size: 1rem;
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
}

.fullscreen-info-location {
  font-size: 0.875rem;
  color: #cbd5e1;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fullscreen-info-badge {
  font-size: 0.75rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 10px;
  border-radius: 4px;
  white-space: nowrap;
}

/* Ошибка в полноэкранном режиме */
.fullscreen-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 20;
  color: #dc2626;
  font-size: 1.25rem;
  text-align: center;
  background: rgba(0, 0, 0, 0.6);
  padding: 16px 24px;
  border-radius: 8px;
}
CSSEOF
echo "  ✔ styles.css (чистый fullscreen + стиль пустых ячеек)"

# ------------------------------------------------------------
# Проверка
# ------------------------------------------------------------
for f in frontend/src/components/FullscreenCamera.jsx frontend/src/pages/MonitorPage.jsx frontend/src/styles.css; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Исправления применены"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Полноэкранный режим:"
echo "  • Убрана красная кнопка «Закрыть»"
echo "  • Убрана шапка — видео на весь экран без отступов"
echo "  • Имя камеры — автоскрываемый оверлей (3 сек без движения мыши)"
echo "  • Выход: двойной клик по видео / Esc"
echo ""
echo "📋 Сетка:"
echo "  • Пустые ячейки рендеруются и помечаются цветом"
echo "  • Стильный значок «объектив» в центре"
echo "  • Для набора 🏢 210: 56 ячеек (8×7), 53 камеры → 3 пустых"
echo "  • Для набора 🏢 301A: 36 ячеек (6×6), 32 камеры → 4 пустых"
echo "  • Для набора 🏢 403: 30 ячеек (6×5), 29 камер → 1 пустая"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 (Ctrl+Shift+R)"
echo "  4. Двойной клик на камеру → чистый полноэкранный режим"
echo "  5. Двойной клик по видео или Esc → выход"