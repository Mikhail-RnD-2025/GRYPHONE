#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 29: ЛОГИКА ПОТОКОВ (sub в сетке, main в full)
#  ------------------------------------------------------------
#  Что меняет:
#    1. CameraCard.jsx — всегда воспроизводит sub (дополнительный) поток
#    2. FullscreenCamera.jsx — всегда воспроизводит main (основной) поток,
#       убрана кнопка переключения, добавлен выход по двойному клику,
#       режим на весь экран через Fullscreen API
#    3. MonitorPage.jsx — routeId изменён на sub
#    4. styles.css — полноэкранный режим без рамок, на весь экран
#
#  Запуск:   bash 29_stream_logic.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. CameraCard.jsx — всегда sub поток
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/CameraCard.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — карточка камеры (режим сетки)
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v29):
//  • Всегда воспроизводит sub (дополнительный) поток
//  • Двойной клик — открывает полноэкранный режим (main поток)
//  • В сетке показывается лёгкий sub для экономии ресурсов
// ============================================================
import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'

export default function CameraCard({ camera, status, aspectRatio, onContextMenu, onFullscreen }) {
  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  const [error, setError] = useState(null)

  // В сетке всегда используем sub (дополнительный) поток.
  // Если sub нет — fallback на основной.
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

  // Двойной клик — полноэкранный режим (там будет main поток).
  const handleDoubleClick = () => {
    if (onFullscreen) onFullscreen(camera)
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

      {camera.location && (
        <div style={{
          fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }} title={camera.location}>
          📍 {camera.location}
        </div>
      )}

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

        {/* Иконка аудио */}
        {camera.enabled && status === 'в_сети' && (
          <div style={{
            position: 'absolute', bottom: '4px', right: '4px',
            background: 'rgba(0, 0, 0, 0.6)', borderRadius: '4px',
            padding: '2px 6px', fontSize: '0.75rem',
          }}>
            {camera.audio ? '🔊' : '🔇'}
          </div>
        )}

        {/* Индикатор типа потока */}
        {camera.enabled && status === 'в_сети' && (
          <div style={{
            position: 'absolute', top: '4px', left: '4px',
            background: 'rgba(0, 0, 0, 0.6)', borderRadius: '4px',
            padding: '2px 6px', fontSize: '0.7rem', color: '#94a3b8',
          }}>
            {hasSub ? 'SUB' : 'MAIN'}
          </div>
        )}

        {error && (
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#dc2626', fontSize: '0.875rem', textAlign: 'center',
          }}>{error}</div>
        )}

        {!camera.enabled && (
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#94a3b8', fontSize: '0.875rem', textAlign: 'center',
          }}>Камера отключена</div>
        )}
      </div>
    </div>
  )
}
JSXEOF
echo "  ✔ CameraCard.jsx (sub поток, индикатор SUB/MAIN)"

# ============================================================
# 2. FullscreenCamera.jsx — main поток, выход по двойному клику,
#    настоящий fullscreen через Fullscreen API
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/FullscreenCamera.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — полноэкранное окно камеры
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v29):
//  • Всегда воспроизводит main (основной) поток
//  • Убрана кнопка переключения потока
//  • Двойной клик по видео — выход из полноэкранного режима
//  • Настоящий fullscreen через Fullscreen API
//  • Esc — выход
//  • Клик по кнопке "Закрыть" — выход
// ============================================================
import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'

export default function FullscreenCamera({ camera, onClose }) {
  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  const overlayRef = useRef(null)
  const [error, setError] = useState(null)
  const [isFullscreen, setIsFullscreen] = useState(false)

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

  // При монтировании запрашиваем настоящий Fullscreen.
  useEffect(() => {
    const el = overlayRef.current
    if (!el) return

    const requestFs = async () => {
      try {
        if (el.requestFullscreen) await el.requestFullscreen()
        else if (el.webkitRequestFullscreen) await el.webkitRequestFullscreen()
        else if (el.mozRequestFullScreen) await el.mozRequestFullScreen()
        else if (el.msRequestFullscreen) await el.msRequestFullscreen()
        setIsFullscreen(true)
      } catch (e) {
        // Fallback: остаёмся в модальном окне.
        console.warn('Fullscreen API недоступен:', e)
      }
    }

    // Небольшая задержка, чтобы DOM успел отрендериться.
    const timer = setTimeout(requestFs, 100)

    // Слушаем выход из fullscreen.
    const handleFsChange = () => {
      if (!document.fullscreenElement &&
          !document.webkitFullscreenElement &&
          !document.mozFullScreenElement) {
        setIsFullscreen(false)
        onClose()
      }
    }
    document.addEventListener('fullscreenchange', handleFsChange)
    document.addEventListener('webkitfullscreenchange', handleFsChange)
    document.addEventListener('mozfullscreenchange', handleFsChange)

    // Esc — выход.
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEsc)

    return () => {
      clearTimeout(timer)
      document.removeEventListener('fullscreenchange', handleFsChange)
      document.removeEventListener('webkitfullscreenchange', handleFsChange)
      document.removeEventListener('mozfullscreenchange', handleFsChange)
      window.removeEventListener('keydown', handleEsc)

      // При размонтировании выходим из fullscreen.
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {})
      }
    }
  }, [onClose])

  // Двойной клик по видео — выход из полноэкранного режима.
  const handleDoubleClick = () => {
    onClose()
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
      {/* Минималистичный заголовок — только имя камеры и кнопка выхода */}
      <div className="fullscreen-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontWeight: 'bold', fontSize: '1rem', color: '#e0e3e8' }}>
            {camera.name}
          </span>
          {camera.location && (
            <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>
              📍 {camera.location}
            </span>
          )}
          <span style={{
            fontSize: '0.75rem', color: '#94a3b8',
            background: 'rgba(255,255,255,0.1)', padding: '2px 8px',
            borderRadius: '4px',
          }}>
            MAIN • {camera.audio ? '🔊' : '🔇'}
          </span>
        </div>

        <button
          className="btn btn-danger"
          onClick={onClose}
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
          onDoubleClick={handleDoubleClick}
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
          pointerEvents: 'none',
        }}>
          Двойной клик или Esc — выход
        </div>
      </div>
    </div>
  )
}
JSXEOF
echo "  ✔ FullscreenCamera.jsx (main поток, fullscreen API, выход по dblclick)"

# ============================================================
# 3. MonitorPage.jsx — routeId изменён на _sub
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница мониторинга
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v29): статусы читаются по ключу {id}_sub,
//  т.к. в сетке всегда воспроизводится sub поток.
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

  const handleFullscreen = (camera) => {
    setFullscreenCamera(camera)
  }

  const handleCloseFullscreen = () => {
    setFullscreenCamera(null)
  }

  const gridStyle = {
    display: 'grid',
    gap: '12px',
  }

  if (setData && setData.max_columns > 0) {
    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, 1fr)`
  } else {
    gridStyle.gridTemplateColumns = 'repeat(auto-fill, minmax(300px, 1fr))'
  }

  const hasSets = setData && setData.set_id !== ''

  return (
    <div className="page">
      <Header />

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

      {hasSets && cameras.length > 0 && (
        <div style={gridStyle}>
          {cameras.map((camera) => {
            // ИСПРАВЛЕНО (v29): статус читаем по ключу _sub,
            // так как в сетке всегда воспроизводится sub поток.
            // Если субпотока нет, fallback на _main.
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
                aspectRatio={setData?.aspect_ratio || '16:9'}
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
echo "  ✔ MonitorPage.jsx (статусы читаются по ключу _sub)"

# ============================================================
# 4. ContextMenu.jsx — обновлён label кнопки "На весь экран"
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/ContextMenu.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — контекстное меню
//  ИСПРАВЛЕНО (v29): без изменений, обновлён label.
// ============================================================
import { useState, useEffect, useRef } from 'react'
import { toggleCamera, updateComment, updateAudio, updateLocation } from '../api'

export default function ContextMenu({ camera, x, y, onClose, onUpdate, onFullscreen }) {
  const [comment, setComment] = useState(camera.comment || '')
  const [location, setLocation] = useState(camera.location || '')
  const [audio, setAudio] = useState(camera.audio !== false)
  const menuRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  const menuWidth = 260
  const menuHeight = 520
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

  const handleFullscreen = () => {
    if (onFullscreen) onFullscreen(camera)
    onClose()
  }

  const handleToggleAudio = async () => {
    const newAudio = !audio
    setAudio(newAudio)
    try {
      await updateAudio(camera.id, newAudio)
      if (window.addToast) {
        window.addToast(
          newAudio ? `🔊 Аудио включено для ${camera.name}` : `🔇 Аудио выключено для ${camera.name}`,
          'info'
        )
      }
      if (onUpdate) onUpdate()
    } catch (e) {
      console.error('Ошибка переключения аудио:', e)
    }
  }

  const handleSaveLocation = async () => {
    try {
      await updateLocation(camera.id, location)
      if (window.addToast) {
        window.addToast(`📍 Местоположение сохранено: ${camera.name}`, 'success')
      }
      if (onUpdate) onUpdate()
      onClose()
    } catch (e) {
      console.error('Ошибка сохранения местоположения:', e)
    }
  }

  return (
    <div
      ref={menuRef}
      className="context-menu"
      style={{ position: 'fixed', left: adjustedX, top: adjustedY, zIndex: 100 }}
    >
      <div style={{
        fontWeight: 'bold', marginBottom: '12px',
        paddingBottom: '8px', borderBottom: '1px solid #334155',
      }}>
        {camera.name}
      </div>

      <button className="btn btn-primary" onClick={handleFullscreen}>
        🖥 На весь экран (основной поток)
      </button>

      <button
        className={`btn ${camera.enabled ? 'btn-danger' : 'btn-primary'}`}
        onClick={handleToggle}
      >
        {camera.enabled ? 'Отключить' : 'Включить'}
      </button>

      <button
        className={`btn ${audio ? 'btn-primary' : ''}`}
        onClick={handleToggleAudio}
        style={{ background: audio ? '#2563eb' : '#475569' }}
      >
        {audio ? '🔊 Аудио: ВКЛ' : '🔇 Аудио: ВЫКЛ'}
      </button>

      <div style={{ marginTop: '8px', marginBottom: '4px', fontSize: '0.75rem', color: '#94a3b8' }}>
        📍 Местоположение:
      </div>
      <input
        type="text"
        value={location}
        onChange={(e) => setLocation(e.target.value)}
        placeholder="Например: Здание 1, этаж 2"
        style={{
          background: '#0b0d10', color: '#e0e3e8',
          border: '1px solid #334155', borderRadius: '4px',
          padding: '6px 8px', fontSize: '0.875rem',
          width: '100%', marginBottom: '4px',
        }}
      />
      <button className="btn btn-primary" onClick={handleSaveLocation}>
        Сохранить местоположение
      </button>

      <div style={{ marginTop: '8px', marginBottom: '4px', fontSize: '0.75rem', color: '#94a3b8' }}>
        💬 Комментарий:
      </div>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Комментарий..."
        rows={2}
        style={{ width: '100%' }}
      />
      <button className="btn btn-primary" onClick={handleSaveComment}>
        Сохранить комментарий
      </button>

      <button className="btn" onClick={onClose}>
        Закрыть
      </button>
    </div>
  )
}
JSXEOF
echo "  ✔ ContextMenu.jsx (label кнопки обновлён)"

# ============================================================
# 5. styles.css — полноэкранный режим на весь экран
# ============================================================
cat > "$PROJECT_DIR/frontend/src/styles.css" << 'CSSEOF'
/* ============================================================
   GRYPHONE — стили приложения
   ------------------------------------------------------------
   ИСПРАВЛЕНО (v29): полноэкранный режим на весь экран,
   без рамок, чёрный фон.
   ============================================================ */

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

.page {
  padding: 16px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 1.5rem;
  margin-bottom: 16px;
}

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
   Полноэкранный режим (v29) — настоящий fullscreen
   ============================================================ */

.fullscreen-overlay {
  background: #000;
}

/* При активном Fullscreen API убираем все отступы */
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
echo "  ✔ styles.css (полноэкранный режим на весь экран)"

# ------------------------------------------------------------
# Проверка
# ------------------------------------------------------------
for f in frontend/src/components/CameraCard.jsx frontend/src/components/FullscreenCamera.jsx frontend/src/pages/MonitorPage.jsx frontend/src/components/ContextMenu.jsx frontend/src/styles.css; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Логика потоков изменена"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что изменено:"
echo "  • В сетке: субпоток (sub) — лёгкий, экономит ресурсы"
echo "  • В fullscreen: основной поток (main) — высокое качество"
echo "  • Индикатор SUB/MAIN в углу карточки"
echo "  • Убрана кнопка переключения потока"
echo "  • Выход из fullscreen: двойной клик / Esc / кнопка"
echo "  • Настоящий Fullscreen API (на весь экран без рамок)"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 (Ctrl+Shift+R)"
echo "  4. Двойной клик на карточку → полноэкранный режим"
echo "  5. Двойной клик по видео → выход"