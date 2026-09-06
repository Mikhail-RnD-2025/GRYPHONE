#!/usr/bin/env python3
"""
159. update_scripts/159_draft_save_button.py
----------------------------------------------------------------------------
Режим черновика в SetsPage:
  • изменения накапливаются локально, НЕ отправляются сразу
  • кнопка "Сохранить" появляется только при наличии изменений
  • кнопка "Отмена" возвращает к состоянию сервера
  • сохранение шлёт дифф: новые наборы POST, изменённые PUT, удалённые DELETE

ЗАПУСК: python update_scripts/159_draft_save_button.py
"""

import sys
from pathlib import Path


SETS_JSX = r'''import { useState, useEffect } from 'react'
import Header from '../components/Header'
import '../styles/sets.css'

// Нормализация формата API (PATCH-139)
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
  const [serverSets, setServerSets] = useState([])   // источник правды
  const [sets, setSets] = useState([])               // черновик
  const [activeSetId, setActiveSetId] = useState(null)
  const [cameras, setCameras] = useState([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)          // PATCH-159
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

  // === PATCH-159: локальные мутации черновика ===

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

  // === PATCH-159: сохранение диффа на сервер ===

  async function saveChanges() {
    setSaving(true)
    try {
      const serverIds = new Set(serverSets.map(s => s.set_id))
      const draftIds = new Set(sets.map(s => s.set_id))

      // Удалённые
      for (const s of serverSets) {
        if (!draftIds.has(s.set_id)) {
          const res = await fetch(`/api/sets/${s.set_id}`, { method: 'DELETE' })
          if (!res.ok) console.error('[SetsPage] delete failed:', s.set_id)
        }
      }

      // Новые и изменённые
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

  // === Drag & Drop (локально, PATCH-159) ===

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
    setDraggedCamera(null)
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
    setDraggedCamera(null)
    setDropTarget(null)
  }

  if (loading) return <div className="sets-loading">Загрузка...</div>

  const gridCameras = (activeSet ? activeSet.camera_ids : [])
    .map(id => cameras.find(c => c.id === id)).filter(Boolean)
  const maxCols = activeSet ? activeSet.max_columns : 1
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
          {dirty && (
            <span className="sets-dirty">● не сохранено</span>
          )}
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
          <div className="sets-list-panel"
            onDragOver={handleDragOver} onDrop={handleDropOnList}>
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
          </div>
        </div>
      </div>
    </div>
  )
}
'''

CSS_ADD = """
/* PATCH-159: кнопка сохранения и индикатор изменений */
.sets-btn-save { color: #4ade80; border-color: rgba(74, 222, 128, 0.4); }
.sets-btn-save:hover { border-color: #4ade80; background: rgba(74, 222, 128, 0.1); }
.sets-btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
.sets-dirty {
  font-size: 0.75rem;
  color: #fbbf24;
  animation: sets-pulse 1.2s ease-in-out infinite;
}
@keyframes sets-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
"""


def main():
    project_root = Path.cwd()
    jsx_file = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"
    css_file = project_root / "frontend" / "src" / "styles" / "sets.css"

    print("=" * 76)
    print("159: Режим черновика + кнопка Сохранить")
    print("=" * 76)
    print()

    backup = jsx_file.with_suffix(".jsx.bak-159")
    backup.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = SETS_JSX
    if content.count('{') != content.count('}') or \
       content.count('(') != content.count(')'):
        print("  [FAIL] Скобки не сбалансированы — откат")
        sys.exit(1)

    jsx_file.write_text(content, encoding="utf-8")
    print("  [OK] SetsPage.jsx: режим черновика")

    css = css_file.read_text(encoding="utf-8")
    if "PATCH-159" not in css:
        css_file.write_text(css + CSS_ADD, encoding="utf-8")
        print("  [OK] sets.css: стили кнопки сохранения")

    print()
    print("=" * 76)
    print("✅ Готово! Новая логика:")
    print()
    print("  1. Любое изменение → локальный черновик")
    print("     • появляется: ● не сохранено  [💾 Сохранить] [↩ Отмена]")
    print("  2. 💾 Сохранить → дифф на сервер (POST/PUT/DELETE)")
    print("  3. ↩ Отмена → возврат к состоянию сервера")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()