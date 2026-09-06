import { useState, useEffect } from 'react'
import Header from '../components/Header'
import '../styles/sets.css'

// PATCH-139: универсальная нормализация формата API
function normalizeSet(raw, key) {
  let cids = raw.camera_ids
  if (!cids && Array.isArray(raw.cameras)) {
    cids = raw.cameras.map(c => (typeof c === 'string' ? c : c.id))
  }
  return {
    set_id: raw.set_id || raw.id || key,
    name: raw.name || raw.set_name || raw.title || raw.set_id || raw.id || key,
    max_rows: parseInt(raw.max_rows) || 1,    // PATCH-145: дефолт 1x1
    max_columns: parseInt(raw.max_columns) || 1,
    aspect_ratio: raw.aspect_ratio || '16:9',
    camera_ids: Array.isArray(cids) ? cids : [],
  }
}

function normalizeCameras(data) {
  let arr = Array.isArray(data) ? data : data.cameras
  if (arr && !Array.isArray(arr) && typeof arr === 'object') {
    arr = Object.values(arr)
  }
  return Array.isArray(arr) ? arr : []
}

export default function SetsManagerPage() {
  const [sets, setSets] = useState([])
  const [activeSetId, setActiveSetId] = useState(null)
  const [cameras, setCameras] = useState([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [draggedCamera, setDraggedCamera] = useState(null)
  const [dropTarget, setDropTarget] = useState(null)

  useEffect(() => { loadData() }, [])

  async function loadData() {
    setLoading(true)
    try {
      const [setsRes, camsRes] = await Promise.all([
        fetch('/api/sets'),
        fetch('/api/cameras')
      ])
      const setsData = await setsRes.json()
      const camsData = await camsRes.json()

      const rawSets = setsData.sets || setsData
      const setsList = (Array.isArray(rawSets) ? rawSets : Object.entries(rawSets || {})
        .map(([k, v]) => normalizeSet(v, k)))
        .map((s, i) => (s.set_id ? s : normalizeSet(s, String(i))))
      setSets(setsList)
      setCameras(normalizeCameras(camsData))

      const currentRes = await fetch('/api/sets/current')
      const currentData = await currentRes.json()
      setActiveSetId(currentData.set_id || currentData.id || (setsList[0] && setsList[0].set_id))
    } catch (e) {
      console.error('[SetsPage] Ошибка загрузки:', e)
    } finally {
      setLoading(false)
    }
  }

  const activeSet = sets.find(s => s.set_id === activeSetId) || sets[0]
  const filteredCameras = cameras.filter(c =>
    !filter ||
    (c.id || '').toLowerCase().includes(filter.toLowerCase()) ||
    (c.name || '').toLowerCase().includes(filter.toLowerCase())
  )

  async function createSet() {
    const name = prompt('Имя нового набора:', 'Новый набор')
    if (!name) return
    try {  // PATCH-144
      const res = await fetch('/api/sets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, max_rows: 1, max_columns: 1 })  // PATCH-145
      })
      if (res.ok) await loadData()
      else {
        const err = await res.json().catch(() => ({}))
        alert('Ошибка: ' + (err.error || res.status))
      }
    } catch (e) {
      alert('Ошибка сети: ' + e.message)
    }
  }

  async function deleteSet() {
    if (!activeSet) return
    if (!confirm(`Удалить набор "${activeSet.name}"?`)) return
    try {  // PATCH-144
      const res = await fetch(`/api/sets/${activeSet.set_id}`, { method: 'DELETE' })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        alert('Ошибка: ' + (err.error || res.status))
        return
      }
      await loadData()
    } catch (e) {
      alert('Ошибка сети: ' + e.message)
    }
  }

  async function updateSet(patch) {
    if (!activeSet) return
    try {  // PATCH-144
      await fetch(`/api/sets/${activeSet.set_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch)
      })
      await loadData()
    } catch (e) {
      console.error('[SetsPage] Ошибка обновления набора:', e)
    }
  }

  async function removeCameraFromSet(cameraId) {
    if (!activeSet) return
    try {  // PATCH-144
      await fetch(`/api/sets/${activeSet.set_id}/cameras/${cameraId}`, { method: 'DELETE' })
      await loadData()
    } catch (e) {
      console.error('[SetsPage] Ошибка удаления камеры:', e)
    }
  }

  async function updateCamerasOrder(newIds) {
    if (!activeSet) return
    try {  // PATCH-144
      await fetch(`/api/sets/${activeSet.set_id}/cameras/order`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_ids: newIds })
      })
      await loadData()
    } catch (e) {
      console.error('[SetsPage] Ошибка сохранения порядка:', e)
    }
  }

  // --- Drag & Drop ---
  function handleDragStart(e, cam) {
    setDraggedCamera(cam)
    e.dataTransfer.effectAllowed = 'move'
  }
  function handleDragOver(e) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }
  function handleDropOnGrid(e, idx) {
    e.preventDefault()
    if (!draggedCamera || !activeSet) return
    const ids = [...activeSet.camera_ids]
    const from = ids.indexOf(draggedCamera.id)
    if (from === -1) {
      ids.splice(idx, 0, draggedCamera.id)
    } else {
      ids.splice(from, 1)
      ids.splice(idx > from ? idx - 1 : idx, 0, draggedCamera.id)
    }
    updateCamerasOrder(ids)
    setDraggedCamera(null)
    setDropTarget(null)
  }
  function handleDropOnList(e) {
    e.preventDefault()
    if (draggedCamera && activeSet && activeSet.camera_ids.includes(draggedCamera.id)) {
      removeCameraFromSet(draggedCamera.id)
    }
    setDraggedCamera(null)
    setDropTarget(null)
  }

  if (loading) return <div className="sets-loading">Загрузка...</div>

  const gridCameras = (activeSet ? activeSet.camera_ids : [])
    .map(id => cameras.find(c => c.id === id)).filter(Boolean)
  const maxCols = activeSet ? activeSet.max_columns : 1  // PATCH-145
  const maxRows = activeSet ? activeSet.max_rows : 1

  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">📦 Управление наборами</h1>
      <div className="sets-page">
      {/* ВЕРХНЯЯ ПАНЕЛЬ */}
      <div className="sets-topbar">
        <span className="sets-label">Набор:</span>
        <select
          className="sets-select"
          value={activeSet ? activeSet.set_id : ''}
          onChange={(e) => setActiveSetId(e.target.value)}
        >
          {sets.map(s => (
            <option key={s.set_id} value={s.set_id}>
              {s.name} ({s.camera_ids.length} кам.)
            </option>
          ))}
        </select>
        <button className="sets-btn" onClick={createSet}>➕ Создать</button>
        <button className="sets-btn sets-btn-danger" onClick={deleteSet}
          disabled={sets.length <= 1}>🗑 Удалить</button>
        <span className="sets-divider">|</span>
        <span className="sets-label">Имя:</span>
        <input
          className="sets-input sets-input-name"
          type="text"
          value={activeSet ? activeSet.name : ''}
          onChange={(e) => updateSet({ name: e.target.value })}
        />
        <span className="sets-label">Сетка:</span>
        <input
          className="sets-input sets-input-num" type="number" min="1" max="20"
          value={maxCols}
          onChange={(e) => updateSet({ max_columns: parseInt(e.target.value) || 1 })}
        />
        <span className="sets-divider">×</span>
        <input
          className="sets-input sets-input-num" type="number" min="1" max="20"
          value={maxRows}
          onChange={(e) => updateSet({ max_rows: parseInt(e.target.value) || 1 })}
        />
        <span className="sets-counter">
          Камер в наборе: {gridCameras.length} / {maxCols * maxRows}
        </span>
      </div>

      {/* ОСНОВНАЯ ОБЛАСТЬ */}
      <div className="sets-main">
        {/* Слева: список камер */}
        <div className="sets-list-panel"
          onDragOver={handleDragOver} onDrop={handleDropOnList}>
          <input
            className="sets-input sets-search"
            type="text"
            placeholder="🔍 Поиск камер..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <div className="sets-list-count">
            Камер: {filteredCameras.length} из {cameras.length}
          </div>
          <div className="sets-list">
            {filteredCameras.map(cam => {
              const inSet = activeSet && activeSet.camera_ids.includes(cam.id)
              return (
                <div
                  key={cam.id}
                  className={'sets-cam-item' + (inSet ? ' in-set' : '') +
                    (draggedCamera && draggedCamera.id === cam.id ? ' dragging' : '')}
                  draggable
                  onDragStart={(e) => handleDragStart(e, cam)}
                >
                  <div className="sets-cam-name">{cam.name || cam.id}</div>
                  <div className="sets-cam-state">
                    {inSet
                      ? <span className="dot-in">✓ В наборе</span>
                      : cam.enabled
                        ? <span className="dot-on">● Вкл</span>
                        : <span className="dot-off">○ Выкл</span>}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Справа: сетка */}
        <div className="sets-grid-wrap">
          <div
            className="sets-grid"
            style={{
              gridTemplateColumns: `repeat(${maxCols}, 1fr)`,
              gridTemplateRows: `repeat(${maxRows}, 1fr)`
            }}
          >
            {Array.from({ length: maxCols * maxRows }).map((_, idx) => {
              const cam = gridCameras[idx]
              return (
                <div
                  key={idx}
                  className={'sets-cell' + (cam ? ' has-cam' : '') +
                    (dropTarget === idx ? ' drag-over' : '')}
                  onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}
                  onDragLeave={() => setDropTarget(null)}
                  onDrop={(e) => handleDropOnGrid(e, idx)}
                >
                  {cam ? (
                    <div
                      className={'sets-cell-cam' +
                        (draggedCamera && draggedCamera.id === cam.id ? ' dragging' : '')}
                      draggable
                      onDragStart={(e) => handleDragStart(e, cam)}
                    >
                      <div className="sets-cell-name">{cam.name || cam.id}</div>
                      <div className="sets-cell-state">
                        {cam.enabled ? '● Вкл' : '○ Выкл'}
                      </div>
                    </div>
                  ) : (
                    <span className="sets-cell-num">{idx + 1}</span>
                  )}
                </div>
              )
            })}
          </div>
          <div className="sets-hint">
            💡 Перетащите камеру из списка в ячейку или внутри сетки для изменения порядка.
            Drop обратно в список — убирает камеру из набора.
          </div>
        </div>
      </div>
      </div>
    </div>
  )
}
