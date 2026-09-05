#!/usr/bin/env python3
"""
138. update_scripts/138_sets_manager_page.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Заменяет старую страницу управления наборами на новый UI:
  • Слева: список всех камер с фильтром
  • Справа: визуальная сетка активного набора (drag & drop)
  • Сверху: панель управления (создать/удалить/размерность)
  • Сохраняет импорт Excel как отдельную секцию

ЗАПУСК: python update_scripts/138_sets_manager_page.py
"""

import sys
import re
from pathlib import Path


# Новый компонент SetsManagerPage
NEW_COMPONENT = r'''import { useState, useEffect, useRef } from 'react'

export default function SetsManagerPage() {
  const [sets, setSets] = useState([])
  const [activeSetId, setActiveSetId] = useState(null)
  const [cameras, setCameras] = useState([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [draggedCamera, setDraggedCamera] = useState(null)
  const [dropTarget, setDropTarget] = useState(null)
  const fileInputRef = useRef(null)

  // Загрузка данных
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

      const setsList = Object.values(setsData.sets || {})
      setSets(setsList)
      setCameras(camsData.cameras || [])

      // Активный набор
      const currentRes = await fetch('/api/sets/current')
      const currentData = await currentRes.json()
      setActiveSetId(currentData.set_id || setsList[0]?.set_id)
    } catch (e) {
      console.error('Ошибка загрузки:', e)
    } finally {
      setLoading(false)
    }
  }

  const activeSet = sets.find(s => s.set_id === activeSetId)
  const filteredCameras = cameras.filter(c =>
    !filter ||
    c.id.toLowerCase().includes(filter.toLowerCase()) ||
    (c.name || '').toLowerCase().includes(filter.toLowerCase())
  )

  // === API функции ===

  async function createSet() {
    const name = prompt('Имя нового набора:', 'Новый набор')
    if (!name) return
    try {
      const res = await fetch('/api/sets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, max_rows: 4, max_columns: 6 })
      })
      if (res.ok) {
        await loadData()
      }
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

  async function updateSetSize(field, value) {
    if (!activeSet) return
    const num = parseInt(value) || 1
    try {
      await fetch(`/api/sets/${activeSet.set_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [field]: num })
      })
      await loadData()
    } catch (e) {
      console.error('Ошибка:', e)
    }
  }

  async function updateSetName(name) {
    if (!activeSet) return
    try {
      await fetch(`/api/sets/${activeSet.set_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      })
      await loadData()
    } catch (e) {
      console.error('Ошибка:', e)
    }
  }

  async function addCameraToSet(cameraId) {
    if (!activeSet) return
    try {
      await fetch(`/api/sets/${activeSet.set_id}/cameras`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_id: cameraId })
      })
      await loadData()
    } catch (e) {
      console.error('Ошибка:', e)
    }
  }

  async function removeCameraFromSet(cameraId) {
    if (!activeSet) return
    try {
      await fetch(`/api/sets/${activeSet.set_id}/cameras/${cameraId}`, {
        method: 'DELETE'
      })
      await loadData()
    } catch (e) {
      console.error('Ошибка:', e)
    }
  }

  async function updateCamerasOrder(newCameraIds) {
    if (!activeSet) return
    try {
      await fetch(`/api/sets/${activeSet.set_id}/cameras/order`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_ids: newCameraIds })
      })
    } catch (e) {
      console.error('Ошибка:', e)
    }
  }

  // === Drag & Drop handlers ===

  function handleDragStart(e, camera) {
    setDraggedCamera(camera)
    e.dataTransfer.effectAllowed = 'move'
  }

  function handleDragOver(e) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  function handleDropOnGrid(e, targetIndex) {
    e.preventDefault()
    if (!draggedCamera || !activeSet) return

    const currentIds = [...activeSet.camera_ids]
    const draggedIdx = currentIds.indexOf(draggedCamera.id)

    if (draggedIdx === -1) {
      // Камера из списка → в сетку
      currentIds.splice(targetIndex, 0, draggedCamera.id)
    } else {
      // Перестановка внутри сетки
      currentIds.splice(draggedIdx, 1)
      const adjustedIdx = targetIndex > draggedIdx ? targetIndex - 1 : targetIndex
      currentIds.splice(adjustedIdx, 0, draggedCamera.id)
    }

    updateCamerasOrder(currentIds)
    setDraggedCamera(null)
    setDropTarget(null)
  }

  function handleDropOnList(e) {
    e.preventDefault()
    if (!draggedCamera || !activeSet) return
    if (activeSet.camera_ids.includes(draggedCamera.id)) {
      removeCameraFromSet(draggedCamera.id)
    }
    setDraggedCamera(null)
    setDropTarget(null)
  }

  // === Импорт Excel ===

  async function handleImportExcel(e) {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch('/api/import/excel', { method: 'POST', body: formData })
      const data = await res.json()
      if (data.success) {
        alert(`Импортировано: ${data.imported || 0} камер`)
        await loadData()
      } else {
        alert('Ошибка импорта: ' + (data.msg || 'неизвестно'))
      }
    } catch (err) {
      alert('Ошибка: ' + err.message)
    }
    e.target.value = ''
  }

  if (loading) return <div style={{padding: 20}}>Загрузка...</div>

  const gridCameras = activeSet?.camera_ids.map(id => cameras.find(c => c.id === id)).filter(Boolean) || []
  const maxCols = activeSet?.max_columns || 8
  const maxRows = activeSet?.max_rows || 7

  return (
    <div style={{display: 'flex', flexDirection: 'column', height: '100vh', padding: 16, gap: 12}}>
      {/* ВЕРХНЯЯ ПАНЕЛЬ */}
      <div style={{
        display: 'flex', gap: 12, alignItems: 'center', padding: '8px 12px',
        background: '#f5f5f5', borderRadius: 8, flexWrap: 'wrap'
      }}>
        <label style={{fontWeight: 600}}>Набор:</label>
        <select
          value={activeSetId || ''}
          onChange={(e) => setActiveSetId(e.target.value)}
          style={{padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc', minWidth: 160}}
        >
          {sets.map(s => <option key={s.set_id} value={s.set_id}>{s.name} ({s.set_id})</option>)}
        </select>
        <button onClick={createSet} style={btnStyle}>➕ Создать</button>
        <button onClick={deleteSet} disabled={sets.length <= 1} style={{...btnStyle, color: '#c00'}}>
          🗑 Удалить
        </button>
        <span style={{margin: '0 8px', color: '#666'}}>|</span>
        <label>Имя:</label>
        <input
          type="text"
          value={activeSet?.name || ''}
          onChange={(e) => updateSetName(e.target.value)}
          style={{padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc', width: 180}}
        />
        <label>Сетка:</label>
        <input
          type="number" min="1" max="20"
          value={activeSet?.max_columns || 8}
          onChange={(e) => updateSetSize('max_columns', e.target.value)}
          style={{width: 60, padding: '6px', borderRadius: 4, border: '1px solid #ccc'}}
        />
        <span>×</span>
        <input
          type="number" min="1" max="20"
          value={activeSet?.max_rows || 7}
          onChange={(e) => updateSetSize('max_rows', e.target.value)}
          style={{width: 60, padding: '6px', borderRadius: 4, border: '1px solid #ccc'}}
        />
        <span style={{marginLeft: 'auto', color: '#666', fontSize: 13}}>
          Камер в наборе: {gridCameras.length} / {maxCols * maxRows}
        </span>
      </div>

      {/* ОСНОВНАЯ ОБЛАСТЬ */}
      <div style={{display: 'flex', gap: 12, flex: 1, minHeight: 0}}>
        {/* ЛЕВАЯ ПАНЕЛЬ: список камер */}
        <div
          onDragOver={handleDragOver}
          onDrop={handleDropOnList}
          style={{
            width: 280, flexShrink: 0, display: 'flex', flexDirection: 'column',
            background: '#fafafa', borderRadius: 8, padding: 12,
            border: dropTarget === 'list' ? '2px dashed #1976d2' : '1px solid #e0e0e0'
          }}
        >
          <input
            type="text"
            placeholder="🔍 Поиск камер..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{padding: '8px 12px', borderRadius: 4, border: '1px solid #ccc', marginBottom: 8}}
          />
          <div style={{fontSize: 12, color: '#666', marginBottom: 8}}>
            Камер: {filteredCameras.length} из {cameras.length}
          </div>
          <div style={{overflowY: 'auto', flex: 1}}>
            {filteredCameras.map(cam => {
              const inSet = activeSet?.camera_ids.includes(cam.id)
              return (
                <div
                  key={cam.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, cam)}
                  style={{
                    padding: '6px 10px', marginBottom: 4, borderRadius: 4,
                    background: inSet ? '#e3f2fd' : '#fff',
                    border: '1px solid ' + (inSet ? '#90caf9' : '#e0e0e0'),
                    cursor: 'grab', fontSize: 13,
                    opacity: draggedCamera?.id === cam.id ? 0.5 : 1
                  }}
                >
                  <div style={{fontWeight: 500}}>{cam.name || cam.id}</div>
                  <div style={{fontSize: 11, color: '#888'}}>
                    {inSet ? '✓ В наборе' : cam.enabled ? '● Вкл' : '○ Выкл'}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* ПРАВАЯ ПАНЕЛЬ: сетка набора */}
        <div style={{flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0}}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${maxCols}, 1fr)`,
            gridTemplateRows: `repeat(${maxRows}, 1fr)`,
            gap: 4, flex: 1, minHeight: 0,
            background: '#fff', borderRadius: 8, padding: 8,
            border: '1px solid #e0e0e0', overflow: 'auto'
          }}>
            {Array.from({length: maxCols * maxRows}).map((_, idx) => {
              const cam = gridCameras[idx]
              return (
                <div
                  key={idx}
                  onDragOver={(e) => {
                    handleDragOver(e)
                    setDropTarget(idx)
                  }}
                  onDragLeave={() => setDropTarget(null)}
                  onDrop={(e) => handleDropOnGrid(e, idx)}
                  style={{
                    border: '1px solid #ddd', borderRadius: 4,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12, padding: 4, position: 'relative',
                    background: dropTarget === idx ? '#e3f2fd' : (cam ? '#f5f5f5' : '#fafafa'),
                    borderStyle: dropTarget === idx ? 'dashed' : 'solid',
                    borderColor: dropTarget === idx ? '#1976d2' : '#ddd'
                  }}
                >
                  {cam ? (
                    <div
                      draggable
                      onDragStart={(e) => handleDragStart(e, cam)}
                      style={{
                        width: '100%', height: '100%', display: 'flex',
                        flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                        cursor: 'grab', opacity: draggedCamera?.id === cam.id ? 0.5 : 1
                      }}
                    >
                      <div style={{fontWeight: 500, textAlign: 'center', wordBreak: 'break-word'}}>
                        {cam.name || cam.id}
                      </div>
                      <div style={{fontSize: 10, color: '#888'}}>
                        {cam.enabled ? '● Вкл' : '○ Выкл'}
                      </div>
                    </div>
                  ) : (
                    <div style={{color: '#ccc', fontSize: 10}}>{idx + 1}</div>
                  )}
                </div>
              )
            })}
          </div>
          <div style={{fontSize: 12, color: '#666', padding: '6px 0', textAlign: 'center'}}>
            💡 Перетащите камеру из списка в ячейку, или внутри сетки для изменения порядка.
            Drop обратно в список — убирает камеру из набора.
          </div>
        </div>
      </div>

      {/* НИЖНЯЯ ПАНЕЛЬ: импорт Excel */}
      <div style={{
        display: 'flex', gap: 12, alignItems: 'center', padding: '8px 12px',
        background: '#fff9e6', borderRadius: 8, border: '1px solid #ffe082'
      }}>
        <strong>📥 Импорт из Excel:</strong>
        <span style={{fontSize: 12, color: '#666'}}>
          Обязательные колонки: ID, main_url. Опциональные: name, sub_url, enabled, comment, audio, location.
        </span>
        <button onClick={() => fileInputRef.current?.click()} style={btnStyle}>
          Выбрать файл
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          onChange={handleImportExcel}
          style={{display: 'none'}}
        />
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
    frontend_dir = project_root / "frontend"

    print("=" * 76)
    print("138: SetsManagerPage — замена старой страницы")
    print("=" * 76)
    print()

    # 1. Найти текущую страницу с "Import from Excel" или "Total sets"
    print("--- Поиск текущей страницы ---")
    candidates = []
    for jsx_file in frontend_dir.rglob("*.jsx"):
        try:
            text = jsx_file.read_text(encoding="utf-8")
            if "Import from Excel" in text or "Total sets" in text or "Save sets" in text:
                candidates.append(jsx_file)
        except Exception:
            pass

    if not candidates:
        print("  [FAIL] Не найдена страница с импортом Excel")
        print("  Попробуйте: grep -rn 'Import from Excel' frontend/src")
        sys.exit(1)

    if len(candidates) > 1:
        print(f"  [WARN] Найдено несколько файлов:")
        for c in candidates:
            print(f"    - {c.relative_to(project_root)}")

    target_file = candidates[0]
    print(f"  [OK] Целевой файл: {target_file.relative_to(project_root)}")

    # 2. Backup
    backup = target_file.with_suffix(target_file.suffix + ".bak-138")
    backup.write_text(target_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    # 3. Заменяем содержимое
    target_file.write_text(NEW_COMPONENT, encoding="utf-8")
    print("  [OK] Содержимое файла заменено")
    print()

    # 4. Проверка синтаксиса JSX (базовая)
    content = target_file.read_text(encoding="utf-8")
    if content.count('{') != content.count('}'):
        print(f"  [FAIL] Несбалансированные {{ }}: {content.count('{')} vs {content.count('}')}")
        target_file.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)
    if content.count('(') != content.count(')'):
        print(f"  [FAIL] Несбалансированные ( ): {content.count('(')} vs {content.count(')')}")
        target_file.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)
    print("  [OK] Скобки сбалансированы")

    print()
    print("=" * 76)
    print("✅ Готово! SetsManagerPage создана.")
    print()
    print("Что нового:")
    print("  • 🎛 Верхняя панель: выбор набора, создать/удалить, имя, размерность")
    print("  • 📋 Левая панель: список камер с поиском, drag-источник")
    print("  • 🎨 Правая панель: визуальная сетка (drag & drop)")
    print("  • 📥 Нижняя панель: импорт Excel (сохранён)")
    print()
    print("Пересоберите frontend:")
    print("  cd frontend && npm run build")
    print()
    print("Обновите браузер (Ctrl+Shift+R) — страница обновится автоматически")
    print("=" * 76)


if __name__ == "__main__":
    main()