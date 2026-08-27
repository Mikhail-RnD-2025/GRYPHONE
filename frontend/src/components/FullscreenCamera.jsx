// ============================================================
//  GRYPHONE — полноэкранное окно камеры
//  ИСПРАВЛЕНО (v42):
//  • Шапка плавно наезжает сверху (transform: translateY)
//  • Автоскрытие через 3 секунды бездействия
//  • Появление при движении мыши
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

  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  const handleClose = useCallback(() => {
    onCloseRef.current()
  }, [])

  const routeId = `${camera.id}_main`
  const streamUrl = `/hls/camera/${routeId}/index.m3u8`

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

  // ИСПРАВЛЕНО (v42): автоскрытие с анимацией наезда
  useEffect(() => {
    const showInfoTemporarily = () => {
      setShowInfo(true)
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
      hideTimerRef.current = setTimeout(() => setShowInfo(false), 3000)
    }

    showInfoTemporarily()

    window.addEventListener('mousemove', showInfoTemporarily)
    window.addEventListener('mousedown', showInfoTemporarily)
    window.addEventListener('touchstart', showInfoTemporarily)

    return () => {
      window.removeEventListener('mousemove', showInfoTemporarily)
      window.removeEventListener('mousedown', showInfoTemporarily)
      window.removeEventListener('touchstart', showInfoTemporarily)
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
    }
  }, [])

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
        }
      } catch (e) {
        console.warn('Fullscreen API недоступен:', e)
      }
    }

    const timer = setTimeout(requestFs, 150)

    const handleFsChange = () => {
      const active = document.fullscreenElement ||
                     document.webkitFullscreenElement
      if (!active && !unmounted) {
        handleClose()
      }
    }
    document.addEventListener('fullscreenchange', handleFsChange)
    document.addEventListener('webkitfullscreenchange', handleFsChange)

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
      window.removeEventListener('keydown', handleEsc)
    }
  }, [handleClose])

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
      <video
        ref={videoRef}
        muted={false}
        playsInline
        controls={false}
        className="fullscreen-video"
      />

      {/* ИСПРАВЛЕНО (v42): шапка с анимацией наезда */}
      <div className={`fullscreen-info-overlay ${showInfo ? 'visible' : ''}`}>
        <span className="fullscreen-info-name">{camera.name}</span>
        {camera.location && (
          <span className="fullscreen-info-location">📍 {camera.location}</span>
        )}
        <span className="fullscreen-info-badge">
          MAIN • {camera.audio ? '🔊' : '🔇'}
        </span>
      </div>

      {error && (
        <div className="fullscreen-error">
          {error}
        </div>
      )}
    </div>
  )
}
