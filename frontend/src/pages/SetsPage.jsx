import { useState, useEffect, useRef } from 'react'
import Header from '../components/Header'
import '../styles/sets.css'

// Нормализация формата API
function normalizeSet(raw, key) {
  let cids = raw.camera_ids
  if (!cids && Array.isArray(raw.cameras)) {
    cids = raw.cameras.map(c => (typeof c === 'string' ? c : c.id))
  }
  return {
    set_id: raw.set_id || raw.id || key,
    name: raw.name || raw.set_name || raw.title || raw.set_id || raw.id || key,
    max_rows: parseInt(raw.max_rows) || 1,
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

const deepClone = (x) => JSON.parse(JSON.stringify(x))

export default function SetsManagerPage() {
  const [serverSets, setServerSets] = useState([])
  const [sets, setSets] = useState([])
  const [activeSetId, setActiveSetId] = useState(null)
  const [cameras, setCameras] = useState([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [draggedCamera, setDraggedCamera] = useState(null)
  const [dropTarget, setDropTarget] = useState(null)
  const [ctxMenu, setCtxMenu] = useState(null)  // PATCH-160: контекстное меню
  const menuRef = useRef(null)

  useEffect(() => { loadData() }, [])

  // PATCH-160: закрытие контекстного меню по клику вне
  useEffect(() => {
    function handleClickOutside(e) {
      if (ctxMenu && menuRef.current && !menuRef.current.contains(e.target)) {
        setCtxMenu(null)
      }
    }
    if (ctxMenu) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [ctxMenu])

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

      setServerSets(setsList)
      setSets(deepClone(setsList))
      setDirty(false)
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

  function mutateActive(fn) {
    if (!activeSet) return
    setSets(prev => prev.map(s => s.set_id === activeSet.set_id ? fn({ ...s }) : s))
    setDirty(true)
  }

  function createSet() {
    const name = prompt('Имя нового набора:', 'Новый набор')
    if (!name) return
    const set_id = 'set_' + Date.now()
    const fresh = normalizeSet({
      set_id, name, max_rows: 1, max_columns: 1,
      aspect_ratio: '16:9', camera_ids: []
    }, set_id)
    setSets(prev => [...prev, fresh])
    setActiveSetId(set_id)
    setDirty(true)
  }

  function deleteSet() {
    if (!activeSet) return
    if (!confirm(`Удалить набор "${activeSet.name}"?`)) return
    const removedId = activeSet.set_id
    setSets(prev => {
      const next = prev.filter(s => s.set_id !== removedId)
      if (activeSetId === removedId && next.length) {
        setActiveSetId(next[0].set_id)
      }
      return next
    })
    setDirty(true)
  }

  async function saveChanges() {
    setSaving(true)
    try {
      const serverIds = new Set(serverSets.map(s => s.set_id))
      const draftIds = new Set(sets.map(s => s.set_id))

      for (const s of serverSets) {
        if (!draftIds.has(s.set_id)) {
          const res = await fetch(`/api/sets/${s.set_id}`, { method: 'DELETE' })
          if (!res.ok) console.error('[SetsPage] delete failed:', s.set_id)
        }
      }

      for (const s of sets) {
        const payload = {
          name: s.name,
          max_rows: s.max_rows,
          max_columns: s.max_columns,
          aspect_ratio: s.aspect_ratio,
          camera_ids: s.camera_ids
        }
        if (!serverIds.has(s.set_id)) {
          const res = await fetch('/api/sets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ set_id: s.set_id, ...payload })
          })
          if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            console.error('[SetsPage] create failed:', err)
          }
        } else {
          const old = serverSets.find(x => x.set_id === s.set_id)
          if (JSON.stringify(old) !== JSON.stringify(s)) {
            const res = await fetch(`/api/sets/${s.set_id}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
            })
            if (!res.ok) {
              const err = await res.json().catch(() => ({}))
              console.error('[SetsPage] update failed:', err)
            }
          }
        }
      }

      await loadData()
    } catch (e) {
      console.error('[SetsPage] Ошибка сохранения:', e)
      alert('Ошибка сохранения: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  function cancelChanges() {
    if (!confirm('Отменить все несохранённые изменения?')) return
    setSets(deepClone(serverSets))
    setDirty(false)
  }

  // === Drag & Drop (PATCH-160: onDragEnd) ===

  function handleDragStart(e, cam) {
    setDraggedCamera(cam)
    e.dataTransfer.effectAllowed = 'move'
  }

  // PATCH-160: сброс состояния ПОСЛЕ завершения drag
  // (решает проблему "подвисания" ghost-image при drop)
  function handleDragEnd() {
    setDraggedCamera(null)
    setDropTarget(null)
  }

  function handleDragOver(e) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  function handleDropOnGrid(e, idx) {
    e.preventDefault()
    if (!draggedCamera || !activeSet) return
    mutateActive(s => {
      const ids = [...s.camera_ids]
      const from = ids.indexOf(draggedCamera.id)
      if (from === -1) {
        ids.splice(idx, 0, draggedCamera.id)
      } else {
        ids.splice(from, 1)
        ids.splice(idx > from ? idx - 1 : idx, 0, draggedCamera.id)
      }
      s.camera_ids = ids
      return s
    })
    // setDraggedCamera(null) убран — сработает в onDragEnd (PATCH-160)
    setDropTarget(null)
  }

  function handleDropOnList(e) {
    e.preventDefault()
    if (draggedCamera && activeSet && activeSet.camera_ids.includes(draggedCamera.id)) {
      mutateActive(s => {
        s.camera_ids = s.camera_ids.filter(id => id !== draggedCamera.id)
        return s
      })
    }
    // setDraggedCamera(null) убран — сработает в onDragEnd (PATCH-160)
    setDropTarget(null)
  }

  // === PATCH-160: Контекстное меню (ПКМ) ===

  function openCtxMenu(e, type, payload) {
    e.preventDefault()
    e.stopPropagation()
    const rect = e.currentTarget.getBoundingClientRect()
    setCtxMenu({
      x: e.clientX,
      y: e.clientY,
      type,       // 'list-item' | 'grid-cell' | 'grid-empty' | 'grid-area' | 'list-area'
      payload
    })
  }

  function closeCtxMenu() {
    setCtxMenu(null)
  }

  function ctxAddToSet(camId) {
    if (!activeSet) return
    mutateActive(s => {
      if (!s.camera_ids.includes(camId)) {
        s.camera_ids = [...s.camera_ids, camId]
      }
      return s
    })
    closeCtxMenu()
  }

  function ctxRemoveFromSet(camId) {
    if (!activeSet) return
    mutateActive(s => {
      s.camera_ids = s.camera_ids.filter(id => id !== camId)
      return s
    })
    closeCtxMenu()
  }

  function ctxClearSet() {
    if (!activeSet) return
    if (activeSet.camera_ids.length === 0) {
      closeCtxMenu()
      return
    }
    if (!confirm(`Очистить весь набор "${activeSet.name}" (${activeSet.camera_ids.length} камер)?`)) {
      closeCtxMenu()
      return
    }
    mutateActive(s => { s.camera_ids = []; return s })
    closeCtxMenu()
  }

  function ctxAddAllVisible() {
    if (!activeSet) return
    mutateActive(s => {
      const existing = new Set(s.camera_ids)
      const toAdd = filteredCameras.filter(c => !existing.has(c.id)).map(c => c.id)
      s.camera_ids = [...s.camera_ids, ...toAdd]
      return s
    })
    closeCtxMenu()
  }

  if (loading) return <div className="sets-loading">Загрузка...</div>

  const gridCameras = (activeSet ? activeSet.camera_ids : [])
    .map(id => cameras.find(c => c.id === id)).filter(Boolean)
  const maxCols = activeSet ? activeSet.max_columns : 1
  const maxRows = activeSet ? activeSet.max_rows : 1
  // PATCH-166: пропорции ячейки из формата набора
  const cellAspect = ((activeSet && activeSet.aspect_ratio) || '16:9').replace(':', ' / ')

  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">📦 Управление наборами</h1>
      <div className="sets-page">
        {/* ВЕРХНЯЯ ПАНЕЛЬ */}
        <div className="sets-topbar">
          <span className="sets-label">Набор:</span>
          <select
            id="set-selector"
            name="set-selector"
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
            id="set-name"
            name="set-name"
            className="sets-input sets-input-name"
            type="text"
            value={activeSet ? activeSet.name : ''}
            onChange={(e) => mutateActive(s => { s.name = e.target.value; return s })}
          />
          <span className="sets-label">Сетка:</span>
          <input
            id="set-max-columns"
            name="max-columns"
            className="sets-input sets-input-num" type="number" min="1" max="32"
            value={maxCols}
            onChange={(e) => mutateActive(s => { s.max_columns = parseInt(e.target.value) || 1; return s })}
          />
          <span className="sets-divider">×</span>
          <input
            id="set-max-rows"
            name="max-rows"
            className="sets-input sets-input-num" type="number" min="1" max="32"
            value={maxRows}
            onChange={(e) => mutateActive(s => { s.max_rows = parseInt(e.target.value) || 1; return s })}
          />
          <span className="sets-label">Формат:</span>
          <select
            id="set-aspect-ratio"
            name="aspect-ratio"
            className="sets-select sets-select-sm"
            value={activeSet ? activeSet.aspect_ratio : '16:9'}
            onChange={(e) => mutateActive(s => { s.aspect_ratio = e.target.value; return s })}
          >
            <option value="16:9">16:9</option>
            <option value="4:3">4:3</option>
          </select>
          {dirty && <span className="sets-dirty">● не сохранено</span>}
          {dirty && (
            <button className="sets-btn sets-btn-save" onClick={saveChanges}
              disabled={saving}>
              {saving ? '⏳ Сохранение...' : '💾 Сохранить'}
            </button>
          )}
          {dirty && (
            <button className="sets-btn" onClick={cancelChanges}
              disabled={saving}>↩ Отмена</button>
          )}
          <span className="sets-counter">
            Камер в наборе: {gridCameras.length} / {maxCols * maxRows}
          </span>
        </div>

        {/* ОСНОВНАЯ ОБЛАСТЬ */}
        <div className="sets-main">
          {/* Слева: список камер */}
          <div
            className="sets-list-panel"
            onDragOver={handleDragOver}
            onDrop={handleDropOnList}
            onContextMenu={(e) => openCtxMenu(e, 'list-area')}
          >
            <input
              id="sets-search"
              name="search"
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
                const otherSets = sets.filter(s =>
                  (!activeSet || s.set_id !== activeSet.set_id) &&
                  s.camera_ids.includes(cam.id))
                return (
                  <div
                    key={cam.id}
                    className={'sets-cam-item' + (inSet ? ' in-set' : '') +
                      (draggedCamera && draggedCamera.id === cam.id ? ' dragging' : '')}
                    draggable
                    onDragStart={(e) => handleDragStart(e, cam)}
                    onDragEnd={handleDragEnd}
                    onContextMenu={(e) => openCtxMenu(e, 'list-item', { cam })}
                  >
                    <div className="sets-cam-name">{cam.name || cam.id}</div>
                    <div className="sets-cam-state">
                      {inSet
                        ? <span className="dot-in">✓ В наборе</span>
                        : cam.enabled
                          ? <span className="dot-on">● Вкл</span>
                          : <span className="dot-off">○ Выкл</span>}
                      {otherSets.length > 0 && (
                        <span
                          className="sets-cam-others"
                          title={'Также в наборах: ' + otherSets.map(s => s.name).join(', ')}
                        >
                          +{otherSets.length}
                        </span>
                      )}
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
                gridTemplateColumns: `repeat(${maxCols}, minmax(0, 1fr))`  // PATCH-166
              }}
              onContextMenu={(e) => {
                if (e.target.classList.contains('sets-grid')) {
                  openCtxMenu(e, 'grid-area')
                }
              }}
            >
              {Array.from({ length: maxCols * maxRows }).map((_, idx) => {
                const cam = gridCameras[idx]
                return (
                  <div
                    key={idx}
                    className={'sets-cell' + (cam ? ' has-cam' : '') +
                      (dropTarget === idx ? ' drag-over' : '')}
                    style={{ aspectRatio: cellAspect }}
                    onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}
                    onDragLeave={() => setDropTarget(null)}
                    onDrop={(e) => handleDropOnGrid(e, idx)}
                    onContextMenu={(e) => {
                      e.stopPropagation()
                      openCtxMenu(e, cam ? 'grid-cell' : 'grid-empty', { cam, idx })
                    }}
                  >
                    {cam ? (
                      <div
                        className={'sets-cell-cam' +
                          (draggedCamera && draggedCamera.id === cam.id ? ' dragging' : '')}
                        draggable
                        onDragStart={(e) => handleDragStart(e, cam)}
                        onDragEnd={handleDragEnd}
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
          </div>
        </div>

        {/* PATCH-160: Контекстное меню */}
        {ctxMenu && (
          <div
            ref={menuRef}
            className="sets-ctx-menu"
            style={{ left: ctxMenu.x, top: ctxMenu.y }}
          >
            {ctxMenu.type === 'list-item' && (
              <>
                <div className="sets-ctx-title">{ctxMenu.payload.cam.name || ctxMenu.payload.cam.id}</div>
                {activeSet && activeSet.camera_ids.includes(ctxMenu.payload.cam.id)
                  ? (
                    <button className="sets-ctx-item" onClick={() => ctxRemoveFromSet(ctxMenu.payload.cam.id)}>
                      ✕ Убрать из набора
                    </button>
                  )
                  : (
                    <button className="sets-ctx-item" onClick={() => ctxAddToSet(ctxMenu.payload.cam.id)}>
                      ＋ Добавить в набор
                    </button>
                  )
                }
              </>
            )}
            {ctxMenu.type === 'grid-cell' && ctxMenu.payload.cam && (
              <>
                <div className="sets-ctx-title">{ctxMenu.payload.cam.name || ctxMenu.payload.cam.id}</div>
                <button className="sets-ctx-item" onClick={() => ctxRemoveFromSet(ctxMenu.payload.cam.id)}>
                  ✕ Убрать из набора
                </button>
              </>
            )}
            {ctxMenu.type === 'grid-area' && (
              <>
                <div className="sets-ctx-title">Сетка набора</div>
                <button
                  className="sets-ctx-item sets-ctx-danger"
                  onClick={ctxClearSet}
                  disabled={!activeSet || activeSet.camera_ids.length === 0}
                >
                  🗑 Очистить весь набор ({activeSet ? activeSet.camera_ids.length : 0})
                </button>
                <button className="sets-ctx-item" onClick={closeCtxMenu}>
                  ✕ Отмена
                </button>
              </>
            )}
            {ctxMenu.type === 'list-area' && (
              <>
                <div className="sets-ctx-title">Список камер</div>
                <button
                  className="sets-ctx-item"
                  onClick={ctxAddAllVisible}
                  disabled={filteredCameras.length === 0}
                >
                  ＋ Добавить все видимые ({filteredCameras.length})
                </button>
                <button className="sets-ctx-item" onClick={closeCtxMenu}>
                  ✕ Отмена
                </button>
              </>
            )}
            {ctxMenu.type === 'grid-empty' && (
              <>
                <div className="sets-ctx-title">Пустая ячейка #{ctxMenu.payload.idx + 1}</div>
                <button
                  className="sets-ctx-item sets-ctx-danger"
                  onClick={ctxClearSet}
                  disabled={!activeSet || activeSet.camera_ids.length === 0}
                >
                  🗑 Очистить весь набор
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
