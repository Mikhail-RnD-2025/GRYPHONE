#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 40: ИСПРАВЛЕНИЕ ИНТЕРФЕЙСА НАСТРОЕК
#  ------------------------------------------------------------
#  Что исправляет:
#    1. Добавляет раздел "Камеры" с полным редактором
#    2. Исправляет скролл во всех разделах
#    3. Кнопка "Назад к камерам" переносится в шапку
#    4. Селектор наборов убирается со страницы настроек
#
#  ЗАПУСК:  bash update_scripts/40_settings_fix.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/main.py" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
else
    PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
fi

echo "📁 Корень проекта: $PROJECT_DIR"
cd "$PROJECT_DIR"
echo "📂 Рабочая директория: $(pwd)"

# ============================================================
# ЧАСТЬ 1: CamerasEditor.jsx — полный редактор камер
# ============================================================
echo ""
echo "🔧 Создаю редактор камер..."

mkdir -p "$PROJECT_DIR/frontend/src/components"

cat > "$PROJECT_DIR/frontend/src/components/CamerasEditor.jsx" << 'CAMERAS_EDITOR_END'
// ============================================================
//  GRYPHONE — редактор камер
//  ============================================================
import { useState, useEffect } from 'react'
import { getCameras, saveCameras } from '../api'

export default function CamerasEditor() {
  const [cameras, setCameras] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({})

  useEffect(() => {
    loadCameras()
  }, [])

  const loadCameras = async () => {
    try {
      const data = await getCameras()
      setCameras(data)
      setLoading(false)
    } catch (e) {
      console.error('Ошибка загрузки камер:', e)
      if (window.addToast) {
        window.addToast('❌ Ошибка загрузки камер', 'error')
      }
      setLoading(false)
    }
  }

  const handleEdit = (camera) => {
    setEditingId(camera.id)
    setEditForm({ ...camera })
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = cameras.map(c => c.id === editingId ? editForm : c)
      await saveCameras(updated)
      setCameras(updated)
      setEditingId(null)
      setEditForm({})
      if (window.addToast) {
        window.addToast('✅ Камера сохранена', 'success')
      }
    } catch (e) {
      console.error('Ошибка сохранения:', e)
      if (window.addToast) {
        window.addToast('❌ Ошибка сохранения камеры', 'error')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setEditingId(null)
    setEditForm({})
  }

  const handleDelete = async (cameraId) => {
    if (!confirm('Удалить эту камеру?')) return

    try {
      const updated = cameras.filter(c => c.id !== cameraId)
      await saveCameras(updated)
      setCameras(updated)
      if (window.addToast) {
        window.addToast('✅ Камера удалена', 'success')
      }
    } catch (e) {
      console.error('Ошибка удаления:', e)
      if (window.addToast) {
        window.addToast('❌ Ошибка удаления камеры', 'error')
      }
    }
  }

  const handleExport = () => {
    const json = JSON.stringify(cameras, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'cameras.json'
    a.click()
    URL.revokeObjectURL(url)
    if (window.addToast) {
      window.addToast('✅ Камеры экспортированы', 'success')
    }
  }

  const handleImport = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    try {
      const text = await file.text()
      const imported = JSON.parse(text)

      if (!Array.isArray(imported)) {
        throw new Error('Файл должен содержать массив камер')
      }

      const merged = [...cameras]
      imported.forEach(imp => {
        const idx = merged.findIndex(c => c.id === imp.id)
        if (idx >= 0) {
          merged[idx] = imp
        } else {
          merged.push(imp)
        }
      })

      await saveCameras(merged)
      setCameras(merged)

      if (window.addToast) {
        window.addToast(`✅ Импортировано ${imported.length} камер`, 'success')
      }
    } catch (e) {
      console.error('Ошибка импорта:', e)
      if (window.addToast) {
        window.addToast(`❌ Ошибка импорта: ${e.message}`, 'error')
      }
    } finally {
      event.target.value = ''
    }
  }

  if (loading) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Загрузка...</div>
  }

  return (
    <div>
      {/* Панель инструментов */}
      <div style={{
        display: 'flex',
        gap: '12px',
        marginBottom: '20px',
        flexWrap: 'wrap',
      }}>
        <button className="btn btn-primary" onClick={handleExport}>
          📤 Экспорт в JSON
        </button>

        <label className="btn btn-primary" style={{ cursor: 'pointer' }}>
          📥 Импорт из JSON
          <input
            type="file"
            accept=".json"
            onChange={handleImport}
            style={{ display: 'none' }}
          />
        </label>

        <span style={{
          display: 'flex',
          alignItems: 'center',
          color: '#94a3b8',
          fontSize: '0.875rem',
        }}>
          Всего камер: {cameras.length}
        </span>
      </div>

      {/* Таблица камер */}
      <div style={{
        overflowX: 'auto',
        border: '1px solid #334155',
        borderRadius: '8px',
      }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '0.875rem',
        }}>
          <thead>
            <tr style={{
              background: '#1e293b',
              borderBottom: '1px solid #334155',
            }}>
              <th style={{ padding: '12px', textAlign: 'left' }}>ID</th>
              <th style={{ padding: '12px', textAlign: 'left' }}>Имя</th>
              <th style={{ padding: '12px', textAlign: 'left' }}>Основной URL</th>
              <th style={{ padding: '12px', textAlign: 'center' }}>Включена</th>
              <th style={{ padding: '12px', textAlign: 'center' }}>Действия</th>
            </tr>
          </thead>
          <tbody>
            {cameras.map((camera) => (
              <tr
                key={camera.id}
                style={{
                  borderBottom: '1px solid #334155',
                  background: editingId === camera.id ? '#1e293b' : 'transparent',
                }}
              >
                {editingId === camera.id ? (
                  <>
                    <td style={{ padding: '12px' }}>{camera.id}</td>
                    <td style={{ padding: '12px' }}>
                      <input
                        type="text"
                        value={editForm.name || ''}
                        onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                        style={{
                          width: '100%',
                          background: '#0b0d10',
                          color: '#e0e3e8',
                          border: '1px solid #334155',
                          borderRadius: '4px',
                          padding: '6px 8px',
                        }}
                      />
                    </td>
                    <td style={{ padding: '12px' }}>
                      <input
                        type="text"
                        value={editForm.main_url || ''}
                        onChange={(e) => setEditForm({ ...editForm, main_url: e.target.value })}
                        style={{
                          width: '100%',
                          background: '#0b0d10',
                          color: '#e0e3e8',
                          border: '1px solid #334155',
                          borderRadius: '4px',
                          padding: '6px 8px',
                          fontSize: '0.75rem',
                        }}
                      />
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <input
                        type="checkbox"
                        checked={editForm.enabled !== false}
                        onChange={(e) => setEditForm({ ...editForm, enabled: e.target.checked })}
                        style={{ width: '18px', height: '18px' }}
                      />
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <button
                        className="btn btn-primary"
                        onClick={handleSave}
                        disabled={saving}
                        style={{ marginRight: '8px', padding: '4px 12px' }}
                      >
                        {saving ? '...' : '💾'}
                      </button>
                      <button
                        className="btn"
                        onClick={handleCancel}
                        style={{ padding: '4px 12px' }}
                      >
                        ✕
                      </button>
                    </td>
                  </>
                ) : (
                  <>
                    <td style={{ padding: '12px', fontFamily: 'monospace' }}>
                      {camera.id}
                    </td>
                    <td style={{ padding: '12px' }}>
                      {camera.name}
                    </td>
                    <td style={{
                      padding: '12px',
                      fontSize: '0.75rem',
                      fontFamily: 'monospace',
                      color: '#94a3b8',
                      maxWidth: '300px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {camera.main_url}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      {camera.enabled ? '✅' : '❌'}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <button
                        className="btn"
                        onClick={() => handleEdit(camera)}
                        style={{ marginRight: '8px', padding: '4px 12px' }}
                      >
                        ✏️
                      </button>
                      <button
                        className="btn btn-danger"
                        onClick={() => handleDelete(camera.id)}
                        style={{ padding: '4px 12px' }}
                      >
                        🗑️
                      </button>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
CAMERAS_EDITOR_END
echo "  ✔ frontend/src/components/CamerasEditor.jsx"

# ============================================================
# ЧАСТЬ 2: SettingsPage.jsx — добавлена вкладка "Камеры",
#          исправлен скролл, убрана кнопка "Назад" из табов
# ============================================================
echo ""
echo "🔧 Переписываю SettingsPage..."

cat > "$PROJECT_DIR/frontend/src/pages/SettingsPage.jsx" << 'SETTINGS_PAGE_END'
// ============================================================
//  GRYPHONE — страница настроек
//  ИСПРАВЛЕНО (v40):
//  • Добавлена вкладка "Камеры" с редактором
//  • Исправлен скролл во всех разделах
//  • Кнопка "Назад" убрана из табов (теперь в шапке)
// ============================================================
import { useState, useEffect } from 'react'
import Header from '../components/Header'
import Dashboard from '../components/Dashboard'
import Help from '../components/Help'
import CamerasEditor from '../components/CamerasEditor'
import Toasts from '../components/Toasts'
import { getSets, saveSets, getConfig } from '../api'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [setsData, setSetsData] = useState(null)
  const [configData, setConfigData] = useState(null)
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const sets = await getSets()
      setSetsData(sets)
      const config = await getConfig()
      setConfigData(config)
    } catch (e) {
      console.error('Ошибка загрузки данных:', e)
    }
  }

  const handleSaveSets = async () => {
    try {
      await saveSets(setsData)
      if (window.addToast) {
        window.addToast('✅ Наборы сохранены', 'success')
      }
    } catch (e) {
      console.error('Ошибка сохранения наборов:', e)
      if (window.addToast) {
        window.addToast('❌ Ошибка сохранения наборов', 'error')
      }
    }
  }

  const handleExcelImport = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    if (!file.name.endsWith('.xls') && !file.name.endsWith('.xlsx')) {
      if (window.addToast) {
        window.addToast('❌ Неверный формат файла. Используйте .xlsx или .xls', 'error')
      }
      return
    }

    setImporting(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/cameras/import-excel', {
        method: 'POST',
        body: formData,
      })
      const result = await response.json()

      if (result.success) {
        if (window.addToast) {
          window.addToast(`✅ ${result.message}. Нажмите F5`, 'success')
        }
        await loadData()
      } else {
        if (window.addToast) {
          window.addToast(`❌ ${result.message}`, 'error')
        }
      }
    } catch (e) {
      if (window.addToast) {
        window.addToast(`❌ Ошибка импорта: ${e.message}`, 'error')
      }
    } finally {
      setImporting(false)
      event.target.value = ''
    }
  }

  return (
    <div className="page" style={{
      overflowY: 'auto',
      height: '100vh',
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <Header />

      <h1 className="page-title">Настройки</h1>

      {/* Вкладки — без кнопки "Назад" */}
      <div className="tabs">
        <button
          className={`btn ${activeTab === 'dashboard' ? 'btn-primary' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          📊 Дашборд
        </button>
        <button
          className={`btn ${activeTab === 'cameras' ? 'btn-primary' : ''}`}
          onClick={() => setActiveTab('cameras')}
        >
          📹 Камеры
        </button>
        <button
          className={`btn ${activeTab === 'sets' ? 'btn-primary' : ''}`}
          onClick={() => setActiveTab('sets')}
        >
          📦 Наборы
        </button>
        <button
          className={`btn ${activeTab === 'config' ? 'btn-primary' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          ⚙️ Конфигурация
        </button>
        <button
          className={`btn ${activeTab === 'help' ? 'btn-primary' : ''}`}
          onClick={() => setActiveTab('help')}
        >
          ❓ Справка
        </button>
      </div>

      {/* Контент вкладок — со скроллом */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        minHeight: 0,
      }}>
        {activeTab === 'dashboard' && (
          <div className="tab-content">
            <Dashboard />
          </div>
        )}

        {activeTab === 'cameras' && (
          <div className="tab-content">
            <h2>Редактор камер</h2>
            <CamerasEditor />
          </div>
        )}

        {activeTab === 'sets' && (
          <div className="tab-content">
            <h2>Управление наборами камер</h2>

            <div style={{
              marginBottom: '20px',
              padding: '16px',
              background: '#1e293b',
              borderRadius: '8px',
              border: '1px solid #334155',
            }}>
              <h3 style={{ marginBottom: '12px' }}>📥 Импорт из Excel</h3>
              <p style={{ color: '#94a3b8', marginBottom: '12px' }}>
                Обязательные колонки: <strong>ID</strong>, <strong>main_url</strong>.
                Опциональные: name, sub_url, enabled, comment, audio, location.
              </p>
              <label className="btn btn-primary" style={{ cursor: 'pointer' }}>
                {importing ? '⏳ Загрузка...' : '📥 Выбрать Excel файл'}
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleExcelImport}
                  disabled={importing}
                  style={{ display: 'none' }}
                />
              </label>
            </div>

            {setsData ? (
              <div>
                <p>Активный набор: <strong>{setsData.default_set || 'не выбран'}</strong></p>
                <p>Всего наборов: <strong>{Object.keys(setsData.sets || {}).length}</strong></p>

                <div style={{ marginTop: '16px' }}>
                  <button className="btn btn-primary" onClick={handleSaveSets}>
                    💾 Сохранить наборы
                  </button>
                </div>
              </div>
            ) : (
              <p>Загрузка...</p>
            )}
          </div>
        )}

        {activeTab === 'config' && (
          <div className="tab-content">
            <h2>Конфигурация системы</h2>
            {configData ? (
              <pre style={{
                background: '#0b0d10',
                padding: '16px',
                borderRadius: '8px',
                overflow: 'auto',
                fontSize: '0.875rem',
                maxHeight: '600px',
              }}>
                {JSON.stringify(configData, null, 2)}
              </pre>
            ) : (
              <p>Загрузка...</p>
            )}
          </div>
        )}

        {activeTab === 'help' && (
          <div className="tab-content">
            <Help />
          </div>
        )}
      </div>

      <Toasts />
    </div>
  )
}
SETTINGS_PAGE_END
echo "  ✔ frontend/src/pages/SettingsPage.jsx"

# ============================================================
# ЧАСТЬ 3: Header.jsx — кнопка "Назад" в шапке,
#          селектор наборов только на главной странице
# ============================================================
echo ""
echo "🔧 Переписываю Header..."

cat > "$PROJECT_DIR/frontend/src/components/Header.jsx" << 'HEADER_END'
// ============================================================
//  GRYPHONE — шапка приложения
//  ИСПРАВЛЕНО (v40):
//  • Определяет текущую страницу через useLocation
//  • На странице настроек НЕ показывает селектор наборов
//  • На странице настроек показывает кнопку "Назад к камерам"
// ============================================================
import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getSets, switchSet } from '../api'

export default function Header() {
  const [sets, setSets] = useState({})
  const [currentSet, setCurrentSet] = useState('')
  const [clock, setClock] = useState('')
  const location = useLocation()

  const isSettingsPage = location.pathname === '/settings'

  useEffect(() => {
    loadSets()
  }, [])

  useEffect(() => {
    const updateClock = () => {
      const now = new Date()
      setClock(now.toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }))
    }
    updateClock()
    const interval = setInterval(updateClock, 1000)
    return () => clearInterval(interval)
  }, [])

  const loadSets = async () => {
    try {
      const data = await getSets()
      setSets(data.sets || {})
      setCurrentSet(data.default_set || '')
    } catch (e) {
      console.error('Ошибка загрузки наборов:', e)
    }
  }

  const handleSetChange = async (e) => {
    const setId = e.target.value
    setCurrentSet(setId)
    try {
      await switchSet(setId)
    } catch (e) {
      console.error('Ошибка переключения набора:', e)
    }
  }

  return (
    <div className="header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <h1 className="header-title" style={{ margin: 0 }}>GRYPHONE</h1>

        {/* Селектор наборов — только на главной странице */}
        {!isSettingsPage && Object.keys(sets).length > 0 && (
          <select
            className="set-selector"
            value={currentSet}
            onChange={handleSetChange}
          >
            {Object.entries(sets).map(([id, set]) => (
              <option key={id} value={id}>
                {set.name}
              </option>
            ))}
          </select>
        )}

        {/* Кнопка "Назад к камерам" — только на странице настроек */}
        {isSettingsPage && (
          <Link to="/" className="btn">
            ← Назад к камерам
          </Link>
        )}
      </div>

      <div className="header-clock">{clock}</div>
    </div>
  )
}
HEADER_END
echo "  ✔ frontend/src/components/Header.jsx"

# ============================================================
# ЧАСТЬ 4: Обновление CSS для корректного скролла
# ============================================================
echo ""
echo "🔧 Обновляю стили..."

cat > "$PROJECT_DIR/frontend/src/styles.css" << 'STYLES_CSS_END'
/* ============================================================
   GRYPHONE — стили приложения
   ИСПРАВЛЕНО (v40): корректный скролл во всех разделах
   ============================================================ */

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #root {
  height: 100%;
  overflow: hidden;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #0b0d10;
  color: #e0e3e8;
}

/* Страница — основной контейнер со скроллом */
.page {
  padding: 12px;
  max-width: none;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-title {
  font-size: 1.5rem;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #1e293b;
  gap: 12px;
  flex-shrink: 0;
}

.header-title {
  font-size: 1.25rem;
  color: #2563eb;
}

.header-clock {
  font-size: 0.875rem;
  color: #94a3b8;
}

.set-selector {
  background: #1e293b;
  color: #e0e3e8;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.875rem;
  cursor: pointer;
  outline: none;
}
.set-selector:hover { border-color: #2563eb; }
.set-selector:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}

/* Вкладки */
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

/* Контент вкладки — со скроллом */
.tab-content {
  background: #0b0d10;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #1e293b;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

/* Карточка камеры (видеостена) */
.camera-card {
  position: relative;
  overflow: hidden;
  background: #000;
  border: none;
  border-radius: 0;
  padding: 0;
  display: flex;
  min-height: 0;
  height: 100%;
}

.camera-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
  z-index: 1;
}

.camera-card-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
  padding: 3px 6px;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.65) 0%,
    rgba(0, 0, 0, 0.25) 70%,
    transparent 100%
  );
  pointer-events: none;
}

.camera-name {
  font-size: 0.7rem;
  font-weight: 500;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 3px rgba(0, 0, 0, 0.5);
}
.status-dot.online {
  background: #059669;
  box-shadow: 0 0 6px #059669;
}
.status-dot.offline {
  background: #dc2626;
  box-shadow: 0 0 6px #dc2626;
}
.status-dot.connecting {
  background: #d97706;
  box-shadow: 0 0 6px #d97706;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.camera-audio-badge {
  position: absolute;
  bottom: 4px;
  right: 4px;
  z-index: 2;
  background: rgba(0, 0, 0, 0.55);
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 0.7rem;
  pointer-events: none;
}

.camera-stream-badge {
  position: absolute;
  bottom: 4px;
  left: 4px;
  z-index: 2;
  background: rgba(0, 0, 0, 0.55);
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 0.65rem;
  color: #94a3b8;
  pointer-events: none;
}

.camera-overlay-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  color: #94a3b8;
  font-size: 0.8rem;
  text-align: center;
  pointer-events: none;
  white-space: nowrap;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.9);
}

.camera-empty {
  position: relative;
  background: linear-gradient(135deg, #0f1116 0%, #13151c 100%);
  border: 1px dashed #24272f;
  border-radius: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  min-height: 0;
  height: 100%;
}

.camera-empty::before {
  content: '';
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1.5px solid #2e313a;
  background: radial-gradient(
    circle,
    #2e313a 0%,
    #2e313a 22%,
    transparent 23%
  );
  opacity: 0.8;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  white-space: nowrap;
}
.status-online { background: #059669; color: #fff; }
.status-offline { background: #dc2626; color: #fff; }
.status-connecting { background: #d97706; color: #fff; }

.btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  background: #334155;
  color: #e0e3e8;
  text-decoration: none;
  display: inline-block;
}
.btn:hover { background: #475569; }
.btn-primary { background: #2563eb; color: #fff; }
.btn-primary:hover { background: #1d4ed8; }
.btn-danger { background: #dc2626; color: #fff; }
.btn-danger:hover { background: #b91c1c; }

.toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.toast {
  padding: 12px 16px;
  border-radius: 6px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
.toast-success { background: #059669; }
.toast-error { background: #dc2626; }
.toast-info { background: #2563eb; }

.context-menu {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  min-width: 220px;
}

.context-menu .btn {
  width: 100%;
  margin-bottom: 8px;
}

.context-menu textarea {
  background: #0b0d10;
  color: #e0e3e8;
  border: 1px solid #334155;
  border-radius: 4px;
  padding: 8px;
  font-size: 0.875rem;
  resize: vertical;
  font-family: inherit;
}

/* Полноэкранный режим */
.fullscreen-overlay {
  background: #000;
}

.fullscreen-overlay:fullscreen,
.fullscreen-overlay:-webkit-full-screen,
.fullscreen-overlay:-moz-full-screen,
.fullscreen-overlay:-ms-fullscreen {
  width: 100vw !important;
  height: 100vh !important;
  padding: 0 !important;
  margin: 0 !important;
}

.fullscreen-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
  z-index: 1;
}

.fullscreen-info-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 20px;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.7) 0%,
    rgba(0, 0, 0, 0.3) 60%,
    transparent 100%
  );
  pointer-events: none;
  transition: opacity 0.4s ease;
  opacity: 1;
}

.fullscreen-info-overlay.hidden {
  opacity: 0;
}

.fullscreen-info-name {
  font-size: 1rem;
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
}

.fullscreen-info-location {
  font-size: 0.875rem;
  color: #cbd5e1;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fullscreen-info-badge {
  font-size: 0.75rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 10px;
  border-radius: 4px;
  white-space: nowrap;
}

.fullscreen-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 20;
  color: #dc2626;
  font-size: 1.25rem;
  text-align: center;
  background: rgba(0, 0, 0, 0.6);
  padding: 16px 24px;
  border-radius: 8px;
}
STYLES_CSS_END
echo "  ✔ frontend/src/styles.css"

# ============================================================
# Финальная проверка
# ============================================================
echo ""
echo "🔍 Финальная проверка..."

for f in frontend/src/components/CamerasEditor.jsx frontend/src/pages/SettingsPage.jsx frontend/src/components/Header.jsx frontend/src/styles.css; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
  echo "  ✔ $f"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Интерфейс настроек исправлен"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что исправлено:"
echo "  • Добавлена вкладка «📹 Камеры» с полным редактором"
echo "  • Редактор: таблица камер, редактирование, удаление"
echo "  • Экспорт/импорт камер в JSON"
echo "  • Исправлен скролл во всех разделах"
echo "  • Кнопка «Назад к камерам» перенесена в шапку"
echo "  • Селектор наборов убран со страницы настроек"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 (Ctrl+Shift+R)"