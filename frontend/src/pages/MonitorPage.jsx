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
import CameraEmpty from '../components/CameraEmpty'
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
  // ИСПРАВЛЕНО (v43): слушаем событие смены набора из Header
  useEffect(() => {
    const handleSetChanged = () => {
      loadCurrentSet()
    }
    window.addEventListener('set-changed', handleSetChanged)
    return () => {
      window.removeEventListener('set-changed', handleSetChanged)
    }
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
  height: "100%",
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
    <div className="page ">
      <Header />

      {hasSets && cameras.length > 0 && (
        <div className="fullscreen-grid" style={gridStyle}>
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
            <CameraEmpty key={`empty-${i}`} index={i} />
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
