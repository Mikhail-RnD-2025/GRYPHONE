#!/usr/bin/env python3
"""
141. update_scripts/141_sets_page_dark_theme.py
----------------------------------------------------------------------------
Приводит SetsPage к общему стилю приложения:
  • создаёт frontend/src/styles/sets.css (палитра из base.css/forms.css)
  • переписывает SetsPage.jsx с inline-стилей на CSS-классы

ЗАПУСК: python update_scripts/141_sets_page_dark_theme.py
"""

import sys
from pathlib import Path


SETS_CSS = r'''/* ============================================================
   Страница управления наборами (SetsPage)
   Палитра: base.css / forms.css
   ============================================================ */

.sets-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 12px;
  gap: 12px;
  color: #e0e3e8;
  overflow: hidden;
}

/* --- Верхняя панель --------------------------------------- */
.sets-topbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 8px 12px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
}

.sets-label {
  font-size: 0.85rem;
  color: #94a3b8;
  font-weight: 600;
}

.sets-divider {
  color: rgba(51, 65, 85, 0.8);
  margin: 0 4px;
}

.sets-counter {
  margin-left: auto;
  font-size: 0.8rem;
  color: #94a3b8;
}

/* --- Кнопки ------------------------------------------------ */
.sets-btn {
  background: rgba(30, 41, 59, 0.8);
  color: #e0e3e8;
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}
.sets-btn:hover { border-color: #2563eb; background: rgba(30, 41, 59, 1); }
.sets-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.sets-btn-danger { color: #f87171; }
.sets-btn-danger:hover { border-color: #dc2626; }

/* --- Поля ввода / селекты ---------------------------------- */
.sets-input, .sets-select {
  background: rgba(30, 41, 59, 0.6);
  color: #e0e3e8;
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.875rem;
  outline: none;
  transition: border-color 0.2s ease;
}
.sets-input:hover, .sets-select:hover { border-color: #2563eb; }
.sets-input:focus, .sets-select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}
.sets-input-name { width: 180px; }
.sets-input-num { width: 60px; }
.sets-select { min-width: 180px; cursor: pointer; }

/* --- Основная область -------------------------------------- */
.sets-main {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

/* --- Левая панель: список камер ---------------------------- */
.sets-list-panel {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
}

.sets-search { margin-bottom: 8px; }

.sets-list-count {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-bottom: 8px;
}

.sets-list {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}
.sets-list::-webkit-scrollbar { width: 8px; }
.sets-list::-webkit-scrollbar-thumb {
  background: rgba(51, 65, 85, 0.8);
  border-radius: 4px;
}
.sets-list::-webkit-scrollbar-track { background: transparent; }

.sets-cam-item {
  padding: 6px 10px;
  margin-bottom: 4px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(51, 65, 85, 0.4);
  cursor: grab;
  font-size: 0.8rem;
  transition: border-color 0.2s ease, background 0.2s ease;
}
.sets-cam-item:hover { border-color: #2563eb; }
.sets-cam-item.in-set {
  background: rgba(37, 99, 235, 0.15);
  border-color: rgba(37, 99, 235, 0.6);
}
.sets-cam-item.dragging { opacity: 0.5; }

.sets-cam-name { font-weight: 500; }
.sets-cam-state { font-size: 0.7rem; color: #94a3b8; margin-top: 2px; }
.sets-cam-state .dot-on { color: #4ade80; }
.sets-cam-state .dot-off { color: #64748b; }
.sets-cam-state .dot-in { color: #60a5fa; }

/* --- Правая панель: сетка ---------------------------------- */
.sets-grid-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.sets-grid {
  display: grid;
  gap: 4px;
  flex: 1;
  min-height: 0;
  padding: 8px;
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
  overflow: auto;
}

.sets-cell {
  border: 1px solid rgba(51, 65, 85, 0.35);
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  font-size: 0.75rem;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.sets-cell.has-cam { background: rgba(30, 41, 59, 0.7); }
.sets-cell.drag-over {
  border: 1px dashed #2563eb;
  background: rgba(37, 99, 235, 0.12);
}

.sets-cell-cam {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: grab;
  text-align: center;
}
.sets-cell-cam.dragging { opacity: 0.5; }
.sets-cell-name {
  font-weight: 500;
  word-break: break-word;
  color: #e0e3e8;
}
.sets-cell-state { font-size: 0.65rem; color: #94a3b8; }
.sets-cell-num { color: rgba(148, 163, 184, 0.35); font-size: 0.7rem; }

.sets-hint {
  font-size: 0.75rem;
  color: #64748b;
  padding: 6px 0 0;
  text-align: center;
}

.sets-loading { padding: 20px; color: #94a3b8; }
'''


SETS_JSX = r'''import { useState, useEffect } from 'react'
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
    max_rows: parseInt(raw.max_rows) || 4,
    max_columns: parseInt(raw.max_columns) || 6,
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
    const res = await fetch('/api/sets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, max_rows: 4, max_columns: 6 })
    })
    if (res.ok) await loadData()
    else alert('Ошибка: ' + ((await res.json()).error || res.status))
  }

  async function deleteSet() {
    if (!activeSet) return
    if (!confirm(`Удалить набор "${activeSet.name}"?`)) return
    await fetch(`/api/sets/${activeSet.set_id}`, { method: 'DELETE' })
    await loadData()
  }

  async function updateSet(patch) {
    if (!activeSet) return
    await fetch(`/api/sets/${activeSet.set_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch)
    })
    await loadData()
  }

  async function removeCameraFromSet(cameraId) {
    if (!activeSet) return
    await fetch(`/api/sets/${activeSet.set_id}/cameras/${cameraId}`, { method: 'DELETE' })
    await loadData()
  }

  async function updateCamerasOrder(newIds) {
    if (!activeSet) return
    await fetch(`/api/sets/${activeSet.set_id}/cameras/order`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ camera_ids: newIds })
    })
    await loadData()
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
  const maxCols = activeSet ? activeSet.max_columns : 8
  const maxRows = activeSet ? activeSet.max_rows : 7

  return (
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
  )
}
'''


def main():
    project_root = Path.cwd()
    css_file = project_root / "frontend" / "src" / "styles" / "sets.css"
    jsx_file = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"

    print("=" * 76)
    print("141: Тёмная тема для SetsPage (общий стиль приложения)")
    print("=" * 76)
    print()

    # 1. CSS
    backup_css = css_file.with_suffix(".css.bak-141") if css_file.exists() else None
    if backup_css:
        backup_css.write_text(css_file.read_text(encoding="utf-8"), encoding="utf-8")
    css_file.write_text(SETS_CSS, encoding="utf-8")
    print(f"  [OK] {css_file.relative_to(project_root)} создан")

    # 2. JSX
    backup_jsx = jsx_file.with_suffix(".jsx.bak-141")
    backup_jsx.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_jsx.name}")

    content = SETS_JSX
    if content.count('{') != content.count('}') or \
       content.count('(') != content.count(')'):
        print("  [FAIL] Скобки не сбалансированы — откат")
        jsx_file.write_text(backup_jsx.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    jsx_file.write_text(content, encoding="utf-8")
    print(f"  [OK] {jsx_file.relative_to(project_root)} переписан на CSS-классы")
    print()

    print("=" * 76)
    print("✅ Готово! Страница в общем стиле приложения.")
    print()
    print("Палитра (из base.css / forms.css):")
    print("  • Фон body:        #0b0d10")
    print("  • Панели:          rgba(30, 41, 59, 0.6)")
    print("  • Рамки:           rgba(51, 65, 85, 0.4)")
    print("  • Акцент (hover):  #2563eb")
    print("  • В наборе:        синий / зелёный / серый индикаторы")
    print()
    print("Пересоберите frontend:")
    print("  cd frontend && npm run build")
    print("  Ctrl+Shift+R в браузере")
    print("=" * 76)


if __name__ == "__main__":
    main()