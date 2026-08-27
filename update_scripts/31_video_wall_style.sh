#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 31: СТИЛЬ ВИДЕОСТЕНЫ
#  ------------------------------------------------------------
#  Что меняет:
#    • Шапка ячейки компактная, наложена поверх видео,
#      прозрачная (градиент), элементы на ней читаемы
#    • Кадр на всю ширину/высоту ячейки без отступов
#    • Убрана лишняя вложенность блоков
#    • Без закруглений
#    • Расстояние между ячейками 2 пикселя
#
#  Запуск:   bash 31_video_wall_style.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. CameraCard.jsx — компактная структура без вложенности
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/CameraCard.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — карточка камеры (видеостена)
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v31):
//  • Кадр на всю ячейку без отступов и внутренних блоков
//  • Шапка компактная, наложена поверх видео, прозрачная
//  • Без закруглений
// ============================================================
import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'

export default function CameraCard({ camera, status, onContextMenu, onFullscreen }) {
  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  const [error, setError] = useState(null)

  // В сетке субпоток; если его нет — основной.
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
      {/* Видео: заполняет всю ячейку */}
      {camera.enabled && (
        <video
          ref={videoRef}
          muted
          playsInline
          className="camera-video"
        />
      )}

      {/* Шапка: наложение сверху, полупрозрачный градиент */}
      <div className="camera-card-header">
        <span className="camera-name" title={camera.name}>
          {camera.name}
        </span>
        <span className={getStatusDot()} title={statusText} />
      </div>

      {/* Бейдж аудио: наложение снизу справа */}
      {camera.enabled && status === 'в_сети' && (
        <div className="camera-audio-badge">
          {camera.audio ? '🔊' : '🔇'}
        </div>
      )}

      {/* Бейдж типа потока: наложение снизу слева */}
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

      {/* Камера отключена */}
      {!camera.enabled && (
        <div className="camera-overlay-text">
          Отключена
        </div>
      )}
    </div>
  )
}
JSXEOF
echo "  ✔ CameraCard.jsx (компактная структура)"

# ============================================================
# 2. MonitorPage.jsx — gap 2px в сетке
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница мониторинга
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v31): расстояние между ячейками 2 пикселя.
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

  // ИСПРАВЛЕНО (v31): расстояние между ячейками 2 пикселя.
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
echo "  ✔ MonitorPage.jsx (gap 2px)"

# ============================================================
# 3. styles.css — стили видеостены
# ============================================================
cat > "$PROJECT_DIR/frontend/src/styles.css" << 'CSSEOF'
/* ============================================================
   GRYPHONE — стили приложения
   ------------------------------------------------------------
   ИСПРАВЛЕНО (v31): стиль видеостены:
   • Кадр на всю ячейку без отступов
   • Шапка наложена поверх видео, прозрачная
   • Без закруглений
   • Расстояние между ячейками 2 пикселя
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
.set-selector:hover {
  border-color: #2563eb;
}
.set-selector:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}

/* ============================================================
   ИСПРАВЛЕНО (v31): карточка-ячейка видеостены
   ============================================================ */

.camera-card {
  position: relative;
  overflow: hidden;
  background: #000;
  /* Без закруглений, без рамки, без отступов */
  border: none;
  border-radius: 0;
  padding: 0;
  display: flex;
  min-height: 0;
  height: 100%;
}

/* Видео: заполняет всю ячейку */
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

/* ИСПРАВЛЕНО (v31): компактная шапка, наложена поверх видео,
   прозрачная (градиент), элементы на ней читаемы */
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
  /* Прозрачный градиент: тёмный сверху, прозрачный снизу */
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

/* Кружочки статуса (на прозрачном фоне шапки) */
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

/* Бейдж аудио: наложение снизу справа */
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

/* Бейдж типа потока: наложение снизу слева */
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

/* Оверлей с текстом (ошибка/отключена): по центру */
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
echo "  ✔ styles.css (видеостена, без закруглений, шапка-наложение)"

# ------------------------------------------------------------
# Проверка
# ------------------------------------------------------------
for f in frontend/src/components/CameraCard.jsx frontend/src/pages/MonitorPage.jsx frontend/src/styles.css; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Стиль видеостены применён"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что изменено:"
echo "  • Кадр на всю ширину/высоту ячейки без отступов"
echo "  • Шапка: компактная, наложена сверху, прозрачный градиент"
echo "  • Имя камеры и кружочек статуса читаемы на любом фоне"
echo "  • Без закруглений, без лишних рамок"
echo "  • Расстояние между ячейками 2 пикселя"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 (Ctrl+Shift+R)"