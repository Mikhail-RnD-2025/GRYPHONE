#!/usr/bin/env python3
"""
194. update_scripts/194_import_export_buttons.py
----------------------------------------------------------------------------
CamerasEditor: две кнопки «Импорт»/«Экспорт» с dropdown выбора формата:
  • 📤 Экспорт ▼ → В Excel (.xlsx) / В JSON (.json)
  • 📥 Импорт ▼ → Из Excel (.xlsx) / Из JSON (.json)
Всё через API endpoints (PATCH-190..193), без localStorage.

ЗАПУСК: python update_scripts/194_import_export_buttons.py
"""

import sys
from pathlib import Path


def find_project_root():
    p = Path.cwd()
    while True:
        if (p / "frontend").is_dir() and (p / "update_scripts").is_dir():
            return p
        parent = p.parent
        if parent == p:
            print("[FAIL] Не найден корень проекта")
            sys.exit(1)
        p = parent


NEW_IMPORTS = "import { useState, useEffect, useRef } from 'react'  // PATCH-194"

NEW_STATE = """  const [editForm, setEditForm] = useState(null)  // PATCH-189: null вместо editingId
  const [exportOpen, setExportOpen] = useState(false)  // PATCH-194
  const [importOpen, setImportOpen] = useState(false)  // PATCH-194
  const exportRef = useRef(null)  // PATCH-194
  const importRef = useRef(null)  // PATCH-194"""

NEW_EFFECT = """  useEffect(() => {
    loadCameras()
  }, [])

  // PATCH-194: закрытие dropdown по клику вне
  useEffect(() => {
    function handleClickOutside(e) {
      if (exportRef.current && !exportRef.current.contains(e.target)) {
        setExportOpen(false)
      }
      if (importRef.current && !importRef.current.contains(e.target)) {
        setImportOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])"""

NEW_FUNCTIONS = '''  // PATCH-194: экспорт через API (excel или json)
  const handleExport = async (format) => {
    setExportOpen(false)
    try {
      if (format === 'excel') {
        const res = await fetch('/api/cameras/export-excel')
        if (!res.ok) throw new Error('Ошибка экспорта Excel')
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'cameras.xlsx'
        a.click()
        URL.revokeObjectURL(url)
      } else {
        const res = await fetch('/api/cameras/export-json')
        if (!res.ok) throw new Error('Ошибка экспорта JSON')
        const data = await res.json()
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'cameras.json'
        a.click()
        URL.revokeObjectURL(url)
      }
      if (window.addToast) {
        window.addToast('✅ Экспорт завершён', 'success')
      }
    } catch (e) {
      console.error('Ошибка экспорта:', e)
      if (window.addToast) {
        window.addToast('❌ Ошибка экспорта: ' + e.message, 'error')
      }
    }
  }

  // PATCH-194: импорт через API (excel или json), мерж-логика на сервере
  const handleImportFile = async (file, format) => {
    setImportOpen(false)
    try {
      let res
      if (format === 'excel') {
        const formData = new FormData()
        formData.append('file', file)
        res = await fetch('/api/cameras/import-excel', { method: 'POST', body: formData })
      } else {
        const text = await file.text()
        const data = JSON.parse(text)
        res = await fetch('/api/cameras/import-json', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        })
      }
      const result = await res.json()
      if (result.success) {
        if (window.addToast) {
          window.addToast(
            `✅ Импорт: всего ${result.imported} (обновлено ${result.updated || 0}, добавлено ${result.added || 0})`,
            'success'
          )
        }
        await loadCameras()
      } else {
        if (window.addToast) {
          window.addToast('❌ ' + (result.error || 'Ошибка импорта'), 'error')
        }
      }
    } catch (e) {
      console.error('Ошибка импорта:', e)
      if (window.addToast) {
        window.addToast('❌ Ошибка импорта: ' + e.message, 'error')
      }
    }
  }'''

NEW_TOOLBAR = '''      {/* PATCH-194: панель инструментов — 2 кнопки с dropdown */}
      <div style={{
        display: 'flex',
        gap: '12px',
        marginBottom: '20px',
        flexWrap: 'wrap',
        alignItems: 'center',
      }}>
        {/* Экспорт */}
        <div style={{ position: 'relative' }} ref={exportRef}>
          <button
            className="btn btn-primary"
            onClick={() => setExportOpen(o => !o)}
          >
            📤 Экспорт {exportOpen ? '▲' : '▼'}
          </button>
          {exportOpen && (
            <div style={{
              position: 'absolute',
              top: 'calc(100% + 4px)',
              left: 0,
              minWidth: '180px',
              background: 'rgba(15, 23, 42, 0.98)',
              border: '1px solid #334155',
              borderRadius: '6px',
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              zIndex: 100,
              overflow: 'hidden',
            }}>
              <button
                onClick={() => handleExport('excel')}
                style={{
                  display: 'block', width: '100%', padding: '10px 14px',
                  background: 'transparent', border: 'none', color: '#e0e3e8',
                  fontSize: '0.875rem', textAlign: 'left', cursor: 'pointer',
                }}
              >
                📊 В Excel (.xlsx)
              </button>
              <button
                onClick={() => handleExport('json')}
                style={{
                  display: 'block', width: '100%', padding: '10px 14px',
                  background: 'transparent', border: 'none', color: '#e0e3e8',
                  fontSize: '0.875rem', textAlign: 'left', cursor: 'pointer',
                }}
              >
                📄 В JSON (.json)
              </button>
            </div>
          )}
        </div>

        {/* Импорт */}
        <div style={{ position: 'relative' }} ref={importRef}>
          <button
            className="btn btn-primary"
            onClick={() => setImportOpen(o => !o)}
          >
            📥 Импорт {importOpen ? '▲' : '▼'}
          </button>
          {importOpen && (
            <div style={{
              position: 'absolute',
              top: 'calc(100% + 4px)',
              left: 0,
              minWidth: '180px',
              background: 'rgba(15, 23, 42, 0.98)',
              border: '1px solid #334155',
              borderRadius: '6px',
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              zIndex: 100,
              overflow: 'hidden',
            }}>
              <label style={{
                display: 'block', width: '100%', padding: '10px 14px',
                background: 'transparent', border: 'none', color: '#e0e3e8',
                fontSize: '0.875rem', textAlign: 'left', cursor: 'pointer',
              }}>
                📊 Из Excel (.xlsx)
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    const f = e.target.files[0]
                    if (f) handleImportFile(f, 'excel')
                    e.target.value = ''
                  }}
                />
              </label>
              <label style={{
                display: 'block', width: '100%', padding: '10px 14px',
                background: 'transparent', border: 'none', color: '#e0e3e8',
                fontSize: '0.875rem', textAlign: 'left', cursor: 'pointer',
              }}>
                📄 Из JSON (.json)
                <input
                  type="file"
                  accept=".json"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    const f = e.target.files[0]
                    if (f) handleImportFile(f, 'json')
                    e.target.value = ''
                  }}
                />
              </label>
            </div>
          )}
        </div>

        <span style={{
          display: 'flex',
          alignItems: 'center',
          color: '#94a3b8',
          fontSize: '0.875rem',
        }}>
          Всего камер: {cameras.length}
        </span>
      </div>'''


def main():
    root = find_project_root()
    f = root / "frontend" / "src" / "components" / "CamerasEditor.jsx"

    print("=" * 76)
    print("194: две кнопки Импорт/Экспорт с dropdown формата")
    print("=" * 76)
    print()

    b = f.with_suffix(".jsx.bak-194")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "PATCH-194" in c:
        print("  [OK] Уже применён")
        return

    n = 0

    # 1. Импорт useRef
    old = "import { useState, useEffect } from 'react'"
    if old in c:
        c = c.replace(old, NEW_IMPORTS, 1); n += 1
        print("  [OK] useRef импортирован")

    # 2. State + refs
    old = "  const [editForm, setEditForm] = useState(null)  // PATCH-189: null вместо editingId"
    if old in c:
        c = c.replace(old, NEW_STATE, 1); n += 1
        print("  [OK] state dropdown добавлен")

    # 3. useEffect закрытия по клику вне
    old = """  useEffect(() => {
    loadCameras()
  }, [])"""
    if old in c:
        c = c.replace(old, NEW_EFFECT, 1); n += 1
        print("  [OK] useEffect клика вне")

    # 4. Функции handleExport/handleImport → новые
    start = c.find("  const handleExport = () => {")
    end_marker = "  // PATCH-189: предпросмотр собранного URL"
    end = c.find(end_marker)
    if start != -1 and end != -1 and end > start:
        c = c[:start] + NEW_FUNCTIONS + "\n\n" + c[end:]
        n += 1
        print("  [OK] функции импорта/экспорта через API")

    # 5. Панель инструментов
    start = c.find("      {/* Панель инструментов */}")
    end_marker = "      {/* Таблица камер */}"
    end = c.find(end_marker)
    if start != -1 and end != -1 and end > start:
        c = c[:start] + NEW_TOOLBAR + "\n\n" + c[end:]
        n += 1
        print("  [OK] панель инструментов: 2 кнопки + dropdown")

    if n == 5 and c.count('{') == c.count('}'):
        f.write_text(c, encoding="utf-8")
        print("  [OK] Сохранено")
    else:
        print(f"  [FAIL] {n}/5 — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово!")
    print()
    print("UI /cameras:")
    print("  [📤 Экспорт ▼]  [📥 Импорт ▼]  Всего камер: 24")
    print("       │                │")
    print("       ├─ 📊 В Excel    ├─ 📊 Из Excel")
    print("       └─ 📄 В JSON     └─ 📄 Из JSON")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "ui: import/export buttons with format dropdown (PATCH-194)" \\')
    print('  -m "two buttons: Export/Import with Excel|JSON choice" \\')
    print('  -m "all operations via API endpoints, merge logic on server" \\')
    print('  -m "toasts show updated/added counts after import"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()