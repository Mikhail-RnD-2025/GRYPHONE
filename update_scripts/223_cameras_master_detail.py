#!/usr/bin/env python3
"""
223. update_scripts/223_cameras_master_detail.py
----------------------------------------------------------------------------
Переделка /cameras в master-detail layout (как SetsPage):
  • Список камер слева (поиск/фильтр/сортировка)
  • Редактор выбранной камеры справа (inline форма, не модалка)
  • Клик по строке = выбор камеры
  • Выделение активной камеры (голубая подсветка)
  • Empty state: "Выберите камеру или добавьте новую"

ЗАПУСК: python update_scripts/223_cameras_master_detail.py
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


CSS_CONTENT = '''/* ============================================================
   Страница редактора камер (CamerasEditor) — master-detail layout
   Палитра: base.css / forms.css
   ============================================================ */

.cameras-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
  min-height: 0;
  padding: 0 12px 12px;
  gap: 12px;
  color: #e0e3e8;
  overflow: hidden;
}

/* --- Основная область: список + редактор ------------------- */
.cameras-main {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* --- Левая панель: список камер --------------------------- */
.cameras-list-panel {
  width: 380px;
  min-width: 280px;
  display: flex;
  flex-direction: column;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
  overflow: hidden;
}

.cameras-list-toolbar {
  display: flex;
  gap: 8px;
  padding: 10px;
  border-bottom: 1px solid rgba(51, 65, 85, 0.4);
  flex-wrap: wrap;
}

.cameras-search {
  flex: 1;
  min-width: 120px;
  background: rgba(15, 23, 42, 0.6);
  color: #e0e3e8;
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.875rem;
  outline: none;
}
.cameras-search:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}

.cameras-select {
  background: rgba(15, 23, 42, 0.6);
  color: #e0e3e8;
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.875rem;
  cursor: pointer;
}

.cameras-list-count {
  padding: 6px 12px;
  font-size: 0.75rem;
  color: #94a3b8;
  border-bottom: 1px solid rgba(51, 65, 85, 0.4);
}

.cameras-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.cameras-list-item {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(51, 65, 85, 0.3);
  cursor: pointer;
  transition: background 0.15s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}
.cameras-list-item:hover {
  background: rgba(37, 99, 235, 0.1);
}
.cameras-list-item.active {
  background: rgba(37, 99, 235, 0.2);
  border-left: 3px solid #2563eb;
}

.cameras-list-item-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.cameras-list-item-status.on { background: #10b981; }
.cameras-list-item-status.off { background: #64748b; }

.cameras-list-item-info {
  flex: 1;
  min-width: 0;
}
.cameras-list-item-id {
  font-size: 0.85rem;
  font-weight: 600;
  color: #e0e3e8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cameras-list-item-name {
  font-size: 0.75rem;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cameras-list-item-ip {
  font-size: 0.7rem;
  color: #64748b;
  font-family: monospace;
}

.cameras-list-actions {
  padding: 10px;
  border-top: 1px solid rgba(51, 65, 85, 0.4);
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* --- Правая панель: редактор ------------------------------ */
.cameras-editor-panel {
  flex: 1;
  min-width: 400px;
  display: flex;
  flex-direction: column;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
  overflow: hidden;
}

.cameras-editor-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(51, 65, 85, 0.4);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cameras-editor-title {
  font-size: 1rem;
  font-weight: 600;
  color: #e0e3e8;
  margin: 0;
}

.cameras-editor-form {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.cameras-field {
  margin-bottom: 16px;
}

.cameras-label {
  display: block;
  margin-bottom: 4px;
  font-size: 0.875rem;
  color: #94a3b8;
  font-weight: 500;
}

.cameras-input {
  width: 100%;
  background: rgba(15, 23, 42, 0.6);
  color: #e0e3e8;
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.875rem;
  outline: none;
}
.cameras-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}
.cameras-input[readonly] {
  color: #64748b;
  background: rgba(15, 23, 42, 0.3);
}
.cameras-input-mono {
  font-family: monospace;
}

.cameras-row {
  display: flex;
  gap: 12px;
}
.cameras-row > * {
  flex: 1;
}

.cameras-checkbox-row {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
}

.cameras-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.cameras-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.cameras-editor-actions {
  padding: 16px 20px;
  border-top: 1px solid rgba(51, 65, 85, 0.4);
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.cameras-btn {
  background: rgba(30, 41, 59, 0.8);
  color: #e0e3e8;
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}
.cameras-btn:hover {
  border-color: #2563eb;
  background: rgba(30, 41, 59, 1);
}
.cameras-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.cameras-btn-primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.cameras-btn-primary:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
}
.cameras-btn-danger {
  color: #f87171;
}
.cameras-btn-danger:hover {
  border-color: #dc2626;
  background: rgba(220, 38, 38, 0.1);
}

.cameras-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #64748b;
  text-align: center;
  padding: 40px;
}
.cameras-empty-icon {
  font-size: 3rem;
  margin-bottom: 16px;
  opacity: 0.5;
}
.cameras-empty-text {
  font-size: 1rem;
  margin-bottom: 8px;
}
.cameras-empty-hint {
  font-size: 0.875rem;
  color: #475569;
}
'''


JSX_CONTENT = '''import { useState, useEffect, useRef, useMemo } from 'react'
import { getCameras, saveCameras } from '../api'
import '../styles/cameras.css'

export default function CamerasEditor() {
  const [cameras, setCameras] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [editForm, setEditForm] = useState(null)
  const [search, setSearch] = useState('')
  const [enabledFilter, setEnabledFilter] = useState('all')
  const [exportOpen, setExportOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const exportRef = useRef(null)
  const importRef = useRef(null)

  useEffect(() => { loadCameras() }, [])

  useEffect(() => {
    function handleClickOutside(e) {
      if (exportRef.current && !exportRef.current.contains(e.target)) setExportOpen(false)
      if (importRef.current && !importRef.current.contains(e.target)) setImportOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const loadCameras = async () => {
    try {
      const data = await getCameras()
      setCameras(data)
      setLoading(false)
    } catch (e) {
      console.error('Ошибка загрузки камер:', e)
      if (window.addToast) window.addToast('❌ Ошибка загрузки камер', 'error')
      setLoading(false)
    }
  }

  const visibleCameras = useMemo(() => {
    let list = cameras
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      list = list.filter(c =>
        (c.id || '').toLowerCase().includes(q) ||
        (c.name || '').toLowerCase().includes(q) ||
        (c.ipaddress || '').toLowerCase().includes(q))
    }
    if (enabledFilter !== 'all') {
      list = list.filter(c => enabledFilter === 'on' ? c.enabled : !c.enabled)
    }
    return [...list].sort((a, b) =>
      String(a.id || '').localeCompare(String(b.id || ''), undefined, { numeric: true }))
  }, [cameras, search, enabledFilter])

  const handleSelect = (camera) => {
    setSelectedId(camera.id)
    setEditForm({ ...camera })
  }

  const handleAdd = () => {
    const newId = `camera-${Date.now()}`
    const newCamera = {
      id: newId,
      name: '',
      ipaddress: '',
      port: '554',
      login: '',
      pass: '',
      main_url: '',
      sub_url: '',
      sub2_url: '',
      enabled: true,
      audio: true,
      comment: '',
      location: '',
    }
    setCameras([...cameras, newCamera])
    setSelectedId(newId)
    setEditForm(newCamera)
  }

  const handleSave = async () => {
    if (!editForm) return
    setSaving(true)
    try {
      const updated = cameras.map(c => c.id === editForm.id ? editForm : c)
      await saveCameras(updated)
      setCameras(updated)
      if (window.addToast) window.addToast('✅ Камера сохранена', 'success')
    } catch (e) {
      console.error('Ошибка сохранения:', e)
      if (window.addToast) window.addToast('❌ Ошибка сохранения', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedId) return
    if (!confirm('Удалить камеру?')) return
    try {
      const updated = cameras.filter(c => c.id !== selectedId)
      await saveCameras(updated)
      setCameras(updated)
      setSelectedId(null)
      setEditForm(null)
      if (window.addToast) window.addToast('🗑️ Камера удалена', 'success')
    } catch (e) {
      console.error('Ошибка удаления:', e)
      if (window.addToast) window.addToast('❌ Ошибка удаления', 'error')
    }
  }

  const handleExportExcel = async () => {
    try {
      const response = await fetch('/api/cameras/export-excel')
      if (!response.ok) throw new Error('Export failed')
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'cameras.xlsx'
      a.click()
      window.URL.revokeObjectURL(url)
      if (window.addToast) window.addToast('📤 Экспорт завершён', 'success')
    } catch (e) {
      if (window.addToast) window.addToast('❌ Ошибка экспорта', 'error')
    }
    setExportOpen(false)
  }

  const handleImportExcel = async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    try {
      const response = await fetch('/api/cameras/import-excel', {
        method: 'POST',
        body: formData,
      })
      const result = await response.json()
      if (result.success) {
        await loadCameras()
        if (window.addToast) {
          window.addToast(`✅ Импорт: ${result.imported} камер`, 'success')
          if (result.warnings && result.warnings.length > 0) {
            console.warn('Предупреждения импорта:', result.warnings)
          }
        }
      } else {
        if (window.addToast) window.addToast(`❌ ${result.error}`, 'error')
      }
    } catch (e) {
      if (window.addToast) window.addToast('❌ Ошибка импорта', 'error')
    }
    setImportOpen(false)
  }

  if (loading) {
    return (
      <div className="cameras-page">
        <div className="cameras-main">
          <div style={{ padding: '40px', color: '#94a3b8' }}>Загрузка...</div>
        </div>
      </div>
    )
  }

  const selectedCamera = editForm

  return (
    <div className="cameras-page">
      <div className="cameras-main">
        {/* Левая панель: список камер */}
        <div className="cameras-list-panel">
          <div className="cameras-list-toolbar">
            <input
              type="text"
              placeholder="🔍 Поиск..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="cameras-search"
            />
            <select
              value={enabledFilter}
              onChange={(e) => setEnabledFilter(e.target.value)}
              className="cameras-select"
            >
              <option value="all">Все</option>
              <option value="on">Включённые</option>
              <option value="off">Выключенные</option>
            </select>
          </div>
          <div className="cameras-list-count">
            Найдено: {visibleCameras.length} из {cameras.length}
          </div>
          <div className="cameras-list">
            {visibleCameras.map((camera) => (
              <div
                key={camera.id}
                className={`cameras-list-item ${selectedId === camera.id ? 'active' : ''}`}
                onClick={() => handleSelect(camera)}
              >
                <div className={`cameras-list-item-status ${camera.enabled ? 'on' : 'off'}`} />
                <div className="cameras-list-item-info">
                  <div className="cameras-list-item-id">{camera.id}</div>
                  <div className="cameras-list-item-name">{camera.name || '—'}</div>
                  <div className="cameras-list-item-ip">
                    {camera.ipaddress || '—'}:{camera.port || '554'}
                  </div>
                </div>
              </div>
            ))}
            {visibleCameras.length === 0 && (
              <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                {search || enabledFilter !== 'all' ? (
                  <>
                    Ничего не найдено
                    {search && <> по запросу <strong>"{search}"</strong></>}
                    <br />
                    <button
                      onClick={() => { setSearch(''); setEnabledFilter('all') }}
                      className="cameras-btn"
                      style={{ marginTop: '12px' }}
                    >
                      Сбросить фильтры
                    </button>
                  </>
                ) : (
                  'Нет камер'
                )}
              </div>
            )}
          </div>
          <div className="cameras-list-actions">
            <button className="cameras-btn cameras-btn-primary" onClick={handleAdd}>
              + Добавить
            </button>
            <div style={{ position: 'relative', flex: 1 }} ref={exportRef}>
              <button className="cameras-btn" onClick={() => setExportOpen(!exportOpen)}>
                📤 Экспорт
              </button>
              {exportOpen && (
                <div style={{
                  position: 'absolute', bottom: '100%', left: 0, marginBottom: '4px',
                  background: '#1e293b', border: '1px solid #334155', borderRadius: '6px',
                  padding: '8px', zIndex: 10,
                }}>
                  <button className="cameras-btn" onClick={handleExportExcel} style={{ width: '100%' }}>
                    📊 Excel (.xlsx)
                  </button>
                </div>
              )}
            </div>
            <div style={{ position: 'relative', flex: 1 }} ref={importRef}>
              <button className="cameras-btn" onClick={() => setImportOpen(!importOpen)}>
                📥 Импорт
              </button>
              {importOpen && (
                <div style={{
                  position: 'absolute', bottom: '100%', left: 0, marginBottom: '4px',
                  background: '#1e293b', border: '1px solid #334155', borderRadius: '6px',
                  padding: '8px', zIndex: 10,
                }}>
                  <label className="cameras-btn" style={{ display: 'block', cursor: 'pointer', textAlign: 'center' }}>
                    📊 Excel (.xlsx)
                    <input
                      type="file"
                      accept=".xlsx,.xls"
                      style={{ display: 'none' }}
                      onChange={(e) => e.target.files[0] && handleImportExcel(e.target.files[0])}
                    />
                  </label>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Правая панель: редактор */}
        <div className="cameras-editor-panel">
          {selectedCamera ? (
            <>
              <div className="cameras-editor-header">
                <h3 className="cameras-editor-title">
                  {selectedCamera.id ? `Редактирование: ${selectedCamera.id}` : 'Новая камера'}
                </h3>
              </div>
              <div className="cameras-editor-form">
                {/* ID (readonly) */}
                <div className="cameras-field">
                  <label className="cameras-label">ID</label>
                  <input
                    type="text"
                    value={selectedCamera.id || ''}
                    readOnly
                    className="cameras-input"
                  />
                </div>

                {/* Name */}
                <div className="cameras-field">
                  <label className="cameras-label">Имя</label>
                  <input
                    type="text"
                    value={selectedCamera.name || ''}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    className="cameras-input"
                    placeholder="Камера 7"
                  />
                </div>

                {/* IP + Port */}
                <div className="cameras-row">
                  <div className="cameras-field">
                    <label className="cameras-label">IP-адрес</label>
                    <input
                      type="text"
                      value={selectedCamera.ipaddress || ''}
                      onChange={(e) => setEditForm({ ...editForm, ipaddress: e.target.value })}
                      className="cameras-input"
                      placeholder="192.168.1.10"
                    />
                  </div>
                  <div className="cameras-field">
                    <label className="cameras-label">Порт</label>
                    <input
                      type="text"
                      value={selectedCamera.port || '554'}
                      onChange={(e) => setEditForm({ ...editForm, port: e.target.value })}
                      className="cameras-input"
                      placeholder="554"
                    />
                  </div>
                </div>

                {/* Login + Pass */}
                <div className="cameras-row">
                  <div className="cameras-field">
                    <label className="cameras-label">Login</label>
                    <input
                      type="text"
                      value={selectedCamera.login || ''}
                      onChange={(e) => setEditForm({ ...editForm, login: e.target.value })}
                      className="cameras-input"
                      placeholder="admin"
                    />
                  </div>
                  <div className="cameras-field">
                    <label className="cameras-label">Пароль</label>
                    <input
                      type="password"
                      value={selectedCamera.pass || ''}
                      onChange={(e) => setEditForm({ ...editForm, pass: e.target.value })}
                      className="cameras-input"
                      placeholder="••••••"
                    />
                  </div>
                </div>

                {/* Main URL */}
                <div className="cameras-field">
                  <label className="cameras-label">Путь основного потока (main_url)</label>
                  <input
                    type="text"
                    value={selectedCamera.main_url || ''}
                    onChange={(e) => setEditForm({ ...editForm, main_url: e.target.value })}
                    className="cameras-input cameras-input-mono"
                    placeholder="Streaming/Channels/101"
                  />
                </div>

                {/* Sub URL */}
                <div className="cameras-field">
                  <label className="cameras-label">Путь субпотока (sub_url, опционально)</label>
                  <input
                    type="text"
                    value={selectedCamera.sub_url || ''}
                    onChange={(e) => setEditForm({ ...editForm, sub_url: e.target.value })}
                    className="cameras-input cameras-input-mono"
                    placeholder="Streaming/Channels/102"
                  />
                </div>

                {/* Sub2 URL */}
                <div className="cameras-field">
                  <label className="cameras-label">Путь sub2 (sub2_url, опционально)</label>
                  <input
                    type="text"
                    value={selectedCamera.sub2_url || ''}
                    onChange={(e) => setEditForm({ ...editForm, sub2_url: e.target.value })}
                    className="cameras-input cameras-input-mono"
                    placeholder="Streaming/Channels/103"
                  />
                </div>

                {/* Checkboxes */}
                <div className="cameras-checkbox-row">
                  <label className="cameras-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedCamera.enabled || false}
                      onChange={(e) => setEditForm({ ...editForm, enabled: e.target.checked })}
                    />
                    <span>Включена</span>
                  </label>
                  <label className="cameras-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedCamera.audio || false}
                      onChange={(e) => setEditForm({ ...editForm, audio: e.target.checked })}
                    />
                    <span>Аудио</span>
                  </label>
                </div>

                {/* Comment */}
                <div className="cameras-field">
                  <label className="cameras-label">Комментарий</label>
                  <input
                    type="text"
                    value={selectedCamera.comment || ''}
                    onChange={(e) => setEditForm({ ...editForm, comment: e.target.value })}
                    className="cameras-input"
                    placeholder="Описание камеры"
                  />
                </div>

                {/* Location */}
                <div className="cameras-field">
                  <label className="cameras-label">Местоположение</label>
                  <input
                    type="text"
                    value={selectedCamera.location || ''}
                    onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
                    className="cameras-input"
                    placeholder="Этаж 2, коридор"
                  />
                </div>
              </div>
              <div className="cameras-editor-actions">
                <button
                  className="cameras-btn cameras-btn-danger"
                  onClick={handleDelete}
                  disabled={saving}
                >
                  🗑 Удалить
                </button>
                <button
                  className="cameras-btn cameras-btn-primary"
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? '💾 Сохранение...' : '💾 Сохранить'}
                </button>
              </div>
            </>
          ) : (
            <div className="cameras-empty">
              <div className="cameras-empty-icon">📹</div>
              <div className="cameras-empty-text">Выберите камеру</div>
              <div className="cameras-empty-hint">
                Кликните на камеру в списке слева или добавьте новую
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
'''


def main():
    root = find_project_root()

    print("=" * 76)
    print("223: Master-Detail layout для /cameras")
    print("=" * 76)
    print()

    # 1. Создаём CSS
    css_path = root / "frontend" / "src" / "styles" / "cameras.css"
    css_bak = css_path.with_suffix(".css.bak-223")
    if css_path.exists():
        css_bak.write_text(css_path.read_text(encoding="utf-8"), encoding="utf-8")
    css_path.write_text(CSS_CONTENT, encoding="utf-8")
    print(f"  [OK] создан {css_path.name} ({len(CSS_CONTENT.splitlines())} строк)")

    # 2. Переписываем JSX
    jsx_path = root / "frontend" / "src" / "components" / "CamerasEditor.jsx"
    jsx_bak = jsx_path.with_suffix(".jsx.bak-223")
    if jsx_path.exists():
        jsx_bak.write_text(jsx_path.read_text(encoding="utf-8"), encoding="utf-8")
    jsx_path.write_text(JSX_CONTENT, encoding="utf-8")
    print(f"  [OK] переписан {jsx_path.name} ({len(JSX_CONTENT.splitlines())} строк)")

    print()
    print("=" * 76)
    print("✅ PATCH-223 готов! Сборка + проверка:")
    print()
    print(f"  cd {root}/frontend && npm run build")
    print()
    print("Откройте /cameras (Ctrl+F5):")
    print("  • Слева: список камер с поиском/фильтром")
    print("  • Справа: редактор выбранной камеры (inline форма)")
    print("  • Клик по строке = выбор камеры")
    print("  • Активная камера подсвечена голубым")
    print("  • Кнопки: + Добавить / 📥 Импорт / 📤 Экспорт")
    print("  • Empty state: 'Выберите камеру или добавьте новую'")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "refactor(cameras): master-detail layout (PATCH-223)" \\')
    print('  -m "replaced table+modal with list+inline editor (like SetsPage)" \\')
    print('  -m "left panel: camera list with search/filter/sort" \\')
    print('  -m "right panel: inline form for selected camera" \\')
    print('  -m "click to select, blue highlight for active camera" \\')
    print('  -m "preserved: import/export Excel, add/edit/delete, PATCH-219 search"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()