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

// PATCH-169 (monitor): расчёт размера ячейки, чтобы сетка влезала в контейнер
function useFitCellSize(cols, rows, ratio) {
  const ref = useRef(null)
  const [size, setSize] = useState({ w: 0, h: 0 })
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const calc = () => {
      const rect = el.getBoundingClientRect()
      const gap = 4
      const availW = rect.width - 16 - gap * (cols - 1)   // padding 8px*2
      const availH = rect.height - 16 - gap * (rows - 1)
      let w = Math.min(availW / cols, (availH / rows) * ratio)
      w = Math.max(60, Math.floor(w))
      setSize({ w, h: Math.floor(w / ratio) })
    }
    calc()
    const ro = new ResizeObserver(calc)
    ro.observe(el)
    return () => ro.disconnect()
  }, [cols, rows, ratio])
  return [ref, size]
}


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

  // PATCH-169: фиксированный размер ячейки, вписанный в окно
  if (setData && setData.max_columns > 0) {
    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, ${cellSize.w}px)`
    gridStyle.gridAutoRows = `${cellSize.h}px`
  } else {
    gridStyle.gridTemplateColumns = 'repeat(auto-fill, minmax(280px, 1fr))'
  }


  // ИСПРАВЛЕНО (v32): число пустых ячеек для заполнения всей сетки.
  // PATCH-168: пропорции ячейки из формата набора
  const cellAspect = ((setData && setData.aspect_ratio) || '16:9').replace(':', ' / ')
  const hasFixedGrid = setData && setData.max_columns > 0 && setData.max_rows > 0
  const totalCells = hasFixedGrid ? setData.max_columns * setData.max_rows : cameras.length
  const emptyCount = Math.max(0, totalCells - cameras.length)

  const hasSets = setData && setData.set_id !== ''
  // PATCH-169: числовое соотношение и размер ячейки под окно
  const aspectNum = ((setData && setData.aspect_ratio) === '4:3') ? 4 / 3 : 16 / 9
  const maxColsM = (setData && setData.max_columns > 0) ? setData.max_columns : 4
  const maxRowsM = (setData && setData.max_rows > 0) ? setData.max_rows : 3
  const [gridRef, cellSize] = useFitCellSize(maxColsM, maxRowsM, aspectNum)

  return (
    <div className="page monitor-page">
      <Header />

      {hasSets && cameras.length > 0 && (
        <div ref={gridRef} className="fullscreen-grid" style={gridStyle}>
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
