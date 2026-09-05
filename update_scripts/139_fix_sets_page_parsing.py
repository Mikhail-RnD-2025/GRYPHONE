#!/usr/bin/env python3
"""
139. update_scripts/139_fix_sets_page_parsing.py
----------------------------------------------------------------------------
Исправляет SetsPage.jsx: универсальная нормализация формата API.
Обрабатывает варианты полей: name/set_name/title, set_id/id,
camera_ids/cameras (массив id или объектов).

ЗАПУСК: python update_scripts/139_fix_sets_page_parsing.py
"""

import sys
from pathlib import Path


NEW_COMPONENT = r'''import { useState, useEffect, useRef } from 'react'

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
  const fileInputRef = useRef(null)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    setLoading(true)
    try {
      const [setsRes, camsRes] = await Promise.all([
        fetch('/api/sets'),
        fetch('/api/cameras')
      ])
      const setsData = await setsRes.json()
      const camsData = await camsRes.json()

      // Нормализуем наборы
      const rawSets = setsData.sets || setsData
      const setsList = (Array.isArray(rawSets) ? rawSets : Object.entries(rawSets || {})
        .map(([k, v]) => normalizeSet(v, k)))
        .map((s, i) => s.set_id ? s : normalizeSet(s, i))
      setSets(setsList)

      // Нормализуем камеры
      const camsList = normalizeCameras(camsData)
      setCameras(camsList)
      console.log('[SetsPage] Наборов:', setsList.length, 'Камер:', camsList.length)

      // Активный набор
      const currentRes = await fetch('/api/sets/current')
      const currentData = await currentRes.json()
      const curId = currentData.set_id || currentData.id || (setsList[0] && setsList[0].set_id)
      setActiveSetId(curId)
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
    try {
      const res = await fetch('/api/sets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, max_rows: 4, max_columns: 6 })
      })
      if (res.ok) await loadData()
      else alert('Ошибка: ' + (await res.json()).error)
    } catch (e) {
      alert('Ошибка создания: ' + e.message)
    }
  }

  async function deleteSet() {
    if (!activeSet) return
    if (!confirm(`Удалить набор "${activeSet.name}"?`)) return
    try {
      await fetch(`/api/sets/${activeSet.set_id}`, { method: 'DELETE' })
      await loadData()
    } catch (e) {
      alert('Ошибка удаления: ' + e.message)
    }
  }

  async function updateSet(patch) {
    if (!activeSet) return
    try {
      await fetch(`/api/sets/${activeSet.set_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch)
      })
      await loadData()
    } catch (e) {
      console.error('Ошибка обновления:', e)
    }
  }

  async function addCameraToSet(cameraId) {
    if (!activeSet) return
    await fetch(`/api/sets/${activeSet.set_id}/cameras`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ camera_id: cameraId })
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

  // === Drag & Drop ===
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
      updateCamerasOrder(ids)
    } else {
      ids.splice(from, 1)
      const to = idx > from ? idx - 1 : idx
      ids.splice(to, 0, draggedCamera.id)
      updateCamerasOrder(ids)
    }
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

  async function handleImportExcel(e) {
    const file = e.target.files && e.target.files[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await fetch('/api/import/excel', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.success) {
        alert('Импортировано: ' + (data.imported || 0) + ' камер')
        await loadData()
      } else {
        alert('Ошибка импорта: ' + (data.msg || 'неизвестно'))
      }
    } catch (err) {
      alert('Ошибка: ' + err.message)
    }
    e.target.value = ''
  }

  if (loading) return <div style={{ padding: 20 }}>Загрузка...</div>

  const gridCameras = (activeSet ? activeSet.camera_ids : [])
    .map(id => cameras.find(c => c.id === id)).filter(Boolean)
  const maxCols = activeSet ? activeSet.max_columns : 8
  const maxRows = activeSet ? activeSet.max_rows : 7

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: 16, gap: 12 }}>
      {/* ВЕРХНЯЯ ПАНЕЛЬ */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '8px 12px', background: '#f5f5f5', borderRadius: 8, flexWrap: 'wrap' }}>
        <label style={{ fontWeight: 600 }}>Набор:</label>
        <select
          value={activeSet ? activeSet.set_id : ''}
          onChange={(e) => setActiveSetId(e.target.value)}
          style={{ padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc', minWidth: 160 }}
        >
          {sets.map(s => (
            <option key={s.set_id} value={s.set_id}>{s.name} ({s.camera_ids.length} кам.)</option>
          ))}
        </select>
        <button onClick={createSet} style={btnStyle}>➕ Создать</button>
        <button onClick={deleteSet} disabled={sets.length <= 1} style={{ ...btnStyle, color: '#c00' }}>🗑 Удалить</button>
        <span style={{ margin: '0 8px', color: '#666' }}>|</span>
        <label>Имя:</label>
        <input
          type="text"
          value={activeSet ? activeSet.name : ''}
          onChange={(e) => updateSet({ name: e.target.value })}
          style={{ padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc', width: 180 }}
        />
        <label>Сетка:</label>
        <input type="number" min="1" max="20" value={maxCols}
          onChange={(e) => updateSet({ max_columns: parseInt(e.target.value) || 1 })}
          style={{ width: 60, padding: 6, borderRadius: 4, border: '1px solid #ccc' }} />
        <span>×</span>
        <input type="number" min="1" max="20" value={maxRows}
          onChange={(e) => updateSet({ max_rows: parseInt(e.target.value) || 1 })}
          style={{ width: 60, padding: 6, borderRadius: 4, border: '1px solid #ccc' }} />
        <span style={{ marginLeft: 'auto', color: '#666', fontSize: 13 }}>
          Камер в наборе: {gridCameras.length} / {maxCols * maxRows}
        </span>
      </div>

      {/* ОСНОВНАЯ ОБЛАСТЬ */}
      <div style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>
        {/* ЛЕВАЯ ПАНЕЛЬ */}
        <div
          onDragOver={handleDragOver}
          onDrop={handleDropOnList}
          style={{ width: 280, flexShrink: 0, display: 'flex', flexDirection: 'column', background: '#fafafa', borderRadius: 8, padding: 12, border: '1px solid #e0e0e0' }}
        >
          <input
            type="text"
            placeholder="🔍 Поиск камер..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: 4, border: '1px solid #ccc', marginBottom: 8 }}
          />
          <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
            Камер: {filteredCameras.length} из {cameras.length}
          </div>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {filteredCameras.map(cam => {
              const inSet = activeSet && activeSet.camera_ids.includes(cam.id)
              return (
                <div
                  key={cam.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, cam)}
                  style={{ padding: '6px 10px', marginBottom: 4, borderRadius: 4, background: inSet ? '#e3f2fd' : '#fff', border: '1px solid ' + (inSet ? '#90caf9' : '#e0e0e0'), cursor: 'grab', fontSize: 13, opacity: draggedCamera && draggedCamera.id === cam.id ? 0.5 : 1 }}
                >
                  <div style={{ fontWeight: 500 }}>{cam.name || cam.id}</div>
                  <div style={{ fontSize: 11, color: '#888' }}>
                    {inSet ? '✓ В наборе' : cam.enabled ? '● Вкл' : '○ Выкл'}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* ПРАВАЯ ПАНЕЛЬ: СЕТКА */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${maxCols}, 1fr)`, gridTemplateRows: `repeat(${maxRows}, 1fr)`, gap: 4, flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, padding: 8, border: '1px solid #e0e0e0', overflow: 'auto' }}>
            {Array.from({ length: maxCols * maxRows }).map((_, idx) => {
              const cam = gridCameras[idx]
              return (
                <div
                  key={idx}
                  onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}
                  onDragLeave={() => setDropTarget(null)}
                  onDrop={(e) => handleDropOnGrid(e, idx)}
                  style={{ border: '1px solid ' + (dropTarget === idx ? '#1976d2' : '#ddd'), borderStyle: dropTarget === idx ? 'dashed' : 'solid', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, padding: 4, background: dropTarget === idx ? '#e3f2fd' : (cam ? '#f5f5f5' : '#fafafa') }}
                >
                  {cam ? (
                    <div
                      draggable
                      onDragStart={(e) => handleDragStart(e, cam)}
                      style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', cursor: 'grab', opacity: draggedCamera && draggedCamera.id === cam.id ? 0.5 : 1 }}
                    >
                      <div style={{ fontWeight: 500, textAlign: 'center', wordBreak: 'break-word' }}>{cam.name || cam.id}</div>
                      <div style={{ fontSize: 10, color: '#888' }}>{cam.enabled ? '● Вкл' : '○ Выкл'}</div>
                    </div>
                  ) : (
                    <div style={{ color: '#ccc', fontSize: 10 }}>{idx + 1}</div>
                  )}
                </div>
              )
            })}
          </div>
          <div style={{ fontSize: 12, color: '#666', padding: '6px 0', textAlign: 'center' }}>
            💡 Перетащите камеру из списка в ячейку, или внутри сетки для изменения порядка. Drop обратно в список — убирает камеру из набора.
          </div>
        </div>
      </div>

      {/* НИЖНЯЯ ПАНЕЛЬ: ИМПОРТ */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '8px 12px', background: '#fff9e6', borderRadius: 8, border: '1px solid #ffe082' }}>
        <strong>📥 Импорт из Excel:</strong>
        <span style={{ fontSize: 12, color: '#666' }}>
          Обязательные колонки: ID, main_url. Опциональные: name, sub_url, enabled, comment, audio, location.
        </span>
        <button onClick={() => fileInputRef.current && fileInputRef.current.click()} style={btnStyle}>Выбрать файл</button>
        <input ref={fileInputRef} type="file" accept=".xlsx,.xls" onChange={handleImportExcel} style={{ display: 'none' }} />
      </div>
    </div>
  )
}

const btnStyle = {
  padding: '6px 14px',
  borderRadius: 4,
  border: '1px solid #ccc',
  background: '#fff',
  cursor: 'pointer',
  fontSize: 13
}
'''


def main():
    project_root = Path.cwd()
    target = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"

    print("=" * 76)
    print("139: Универсальный парсинг формата API в SetsPage")
    print("=" * 76)
    print()

    if not target.exists():
        print("  [FAIL] SetsPage.jsx не найден")
        sys.exit(1)

    backup = target.with_suffix(".jsx.bak-139")
    backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    target.write_text(NEW_COMPONENT, encoding="utf-8")
    print("  [OK] SetsPage.jsx обновлён (нормализация формата API)")

    content = target.read_text(encoding="utf-8")
    if content.count('{') != content.count('}') or content.count('(') != content.count(')'):
        print("  [FAIL] Скобки не сбалансированы — откат")
        target.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)
    print("  [OK] Скобки сбалансированы")
    print()

    print("=" * 76)
    print("✅ Готово! Пересоберите и проверьте:")
    print("  cd frontend && npm run build")
    print("  Ctrl+Shift+R в браузере")
    print()
    print("Ожидаемо:")
    print("  • Dropdown: '🏢 210 (24 кам.)'")
    print("  • Список слева: 24 камеры")
    print("  • Сетка: камеры набора в ячейках")
    print("=" * 76)


if __name__ == "__main__":
    main()