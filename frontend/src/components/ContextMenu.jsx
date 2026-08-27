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
