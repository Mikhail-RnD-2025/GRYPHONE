// ============================================================
//  GRYPHONE — карточка камеры (видеостена)
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v33):
//  • Видео ВСЕГДА рендерится (не условно) — это гарантирует,
//    что videoRef.current доступен в момент выполнения эффекта
//  • Плеер корректно пересоздаётся при изменении статуса
//    (включение/выключение камеры)
//  • Устранена проблема «поток не появляется без перезагрузки»
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

  // ИСПРАВЛЕНО (v33): shouldPlay не зависит от статуса «недоступна»,
  // т.к. статус может задерживаться. Достаточно флага включена.
  const shouldPlay = camera.enabled

  // ИСПРАВЛЕНО (v33): эффект корректно управляет плеером при
  // изменении статуса камеры. Видео элемент всегда рендерится,
  // поэтому videoRef.current гарантированно доступен.
  useEffect(() => {
    const video = videoRef.current

    // Если не нужно воспроизводить — очищаем плеер и выходим.
    if (!shouldPlay) {
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
      if (video) {
        video.removeAttribute('src')
        video.load()
      }
      setError(null)
      return
    }

    // Если видео элемента нет (не должно случаться, т.к. он
    // всегда рендерится), выходим.
    if (!video) return

    setError(null)

    if (Hls.isSupported()) {
      const hls = new Hls({
        liveSyncDurationCount: 2,
        liveMaxLatencyDurationCount: 4,
        lowLatencyMode: true,
      })
      hls.loadSource(streamUrl)
      hls.attachMedia(video)
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {})
      })
      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          setError('Поток недоступен')
          hls.destroy()
          hlsRef.current = null
        }
      })
      hlsRef.current = hls
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = streamUrl
      video.play().catch(() => setError('Не удалось воспроизвести'))
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
      {/* ИСПРАВЛЕНО (v33): видео ВСЕГДА рендерится (не условно).
          Это гарантирует, что videoRef.current доступен в момент
          выполнения эффекта и плеер создаётся корректно. */}
      <video
        ref={videoRef}
        muted
        playsInline
        className="camera-video"
      />

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

      {/* Камера включена, но недоступна */}
      {camera.enabled && status === 'недоступна' && (
        <div className="camera-overlay-text">
          Недоступна
        </div>
      )}
    </div>
  )
}
