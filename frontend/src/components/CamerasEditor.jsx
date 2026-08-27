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
