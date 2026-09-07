import { useState, useEffect } from 'react'
import { getCameras, saveCameras } from '../api'

export default function CamerasEditor() {
  const [cameras, setCameras] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editForm, setEditForm] = useState(null)  // PATCH-189: null вместо editingId

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
    setEditForm({ ...camera })  // PATCH-189: открываем модалку
  }

  const handleSave = async () => {
    if (!editForm) return
    setSaving(true)
    try {
      const updated = cameras.map(c => c.id === editForm.id ? editForm : c)
      await saveCameras(updated)
      setCameras(updated)
      setEditForm(null)  // PATCH-189: закрываем модалку
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
    setEditForm(null)  // PATCH-189: закрываем модалку
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

  // PATCH-189: предпросмотр собранного URL
  const buildPreviewUrl = () => {
    if (!editForm) return ''
    const { login, pass, ipaddress, port, main_url } = editForm
    if (!ipaddress || !main_url) return ''

    let auth = ''
    if (login) {
      auth = login
      if (pass) auth += `:${pass}`
      auth += '@'
    }

    const p = port || '554'
    const path = main_url.replace(/^\//, '')
    return `rtsp://${auth}${ipaddress}:${p}/${path}`
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
              <th style={{ padding: '12px', textAlign: 'left' }}>IP:Порт</th>
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
                }}
              >
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
                }}>
                  {camera.ipaddress || '—'}:{camera.port || '554'}
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* PATCH-189: Модальное окно редактирования */}
      {editForm && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            background: '#1e293b',
            borderRadius: '8px',
            padding: '24px',
            maxWidth: '600px',
            width: '90%',
            maxHeight: '90vh',
            overflowY: 'auto',
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '20px' }}>
              Редактирование камеры: {editForm.id}
            </h3>

            {/* ID (readonly) */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', color: '#94a3b8' }}>
                ID
              </label>
              <input
                type="text"
                value={editForm.id || ''}
                readOnly
                style={{
                  width: '100%',
                  background: '#0b0d10',
                  color: '#64748b',
                  border: '1px solid #334155',
                  borderRadius: '4px',
                  padding: '8px',
                  fontSize: '0.875rem',
                }}
              />
            </div>

            {/* Name */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', color: '#94a3b8' }}>
                Имя
              </label>
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
                  padding: '8px',
                  fontSize: '0.875rem',
                }}
              />
            </div>

            {/* Login + Pass */}
            <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', color: '#94a3b8' }}>
                  Login
                </label>
                <input
                  type="text"
                  value={editForm.login || ''}
                  onChange={(e) => setEditForm({ ...editForm, login: e.target.value })}
                  placeholder="admin"
                  style={{
                    width: '100%',
                    background: '#0b0d10',
                    color: '#e0e3e8',
                    border: '1px solid #334155',
                    borderRadius: '4px',
                    padding: '8px',
                    fontSize: '0.875rem',
                  }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', color: '#94a3b8' }}>
                  Пароль
                </label>
                <input
                  type="password"
                  value={editForm.pass || ''}
                  onChange={(e) => setEditForm({ ...editForm, pass: e.target.value })}
                  placeholder="••••••"
                  style={{
                    width: '100%',
                    background: '#0b0d10',
                    color: '#e0e3e8',
                    border: '1px solid #334155',
                    borderRadius: '4px',
                    padding: '8px',
                    fontSize: '0.875rem',
                  }}
                />
              </div>
            </div>

            {/* IP + Port */}
            <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
              <div style={{ flex: 2 }}>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', color: '#94a3b8' }}>
                  IP-адрес
                </label>
                <input
                  type="text"
                  value={editForm.ipaddress || ''}
                  onChange={(e) => setEditForm({ ...editForm, ipaddress: e.target.value })}
                  placeholder="192.168.1.10"
                  style={{
                    width: '100%',
                    background: '#0b0d10',
                    color: '#e0e3e8',
                    border: '1px solid #334155',
                    borderRadius: '4px',
                    padding: '8px',
                    fontSize: '0.875rem',
                  }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', color: '#94a3b8' }}>
                  Порт
                </label>
                <input
                  type="text"
                  value={editForm.port || '554'}
                  onChange={(e) => setEditForm({ ...editForm, port: e.target.value })}
                  placeholder="554"
                  style={{
                    width: '100%',
                    background: '#0b0d10',
                    color: '#e0e3e8',
                    border: '1px solid #334155',
                    borderRadius: '4px',
                    padding: '8px',
                    fontSize: '0.875rem',
                  }}
                />
              </div>
            </div>

            {/* Main URL */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', color: '#94a3b8' }}>
                Путь основного потока (main_url)
              </label>
              <input
                type="text"
                value={editForm.main_url || ''}
                onChange={(e) => setEditForm({ ...editForm, main_url: e.target.value })}
                placeholder="Streaming/Channels/101"
                style={{
                  width: '100%',
                  background: '#0b0d10',
                  color: '#e0e3e8',
                  border: '1px solid #334155',
                  borderRadius: '4px',
                  padding: '8px',
                  fontSize: '0.875rem',
                  fontFamily: 'monospace',
                }}
              />
            </div>

            {/* Sub URL */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', color: '#94a3b8' }}>
                Путь субпотока (sub_url, опционально)
              </label>
              <input
                type="text"
                value={editForm.sub_url || ''}
                onChange={(e) => setEditForm({ ...editForm, sub_url: e.target.value })}
                placeholder="Streaming/Channels/102"
                style={{
                  width: '100%',
                  background: '#0b0d10',
                  color: '#e0e3e8',
                  border: '1px solid #334155',
                  borderRadius: '4px',
                  padding: '8px',
                  fontSize: '0.875rem',
                  fontFamily: 'monospace',
                }}
              />
            </div>

            {/* Sub2 URL */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', color: '#94a3b8' }}>
                Путь sub2 (задел на будущее, опционально)
              </label>
              <input
                type="text"
                value={editForm.sub2_url || ''}
                onChange={(e) => setEditForm({ ...editForm, sub2_url: e.target.value })}
                placeholder=""
                style={{
                  width: '100%',
                  background: '#0b0d10',
                  color: '#e0e3e8',
                  border: '1px solid #334155',
                  borderRadius: '4px',
                  padding: '8px',
                  fontSize: '0.875rem',
                  fontFamily: 'monospace',
                }}
              />
            </div>

            {/* Предпросмотр URL */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', color: '#94a3b8' }}>
                Предпросмотр собранного URL
              </label>
              <input
                type="text"
                value={buildPreviewUrl()}
                readOnly
                style={{
                  width: '100%',
                  background: '#0b0d10',
                  color: '#64748b',
                  border: '1px solid #334155',
                  borderRadius: '4px',
                  padding: '8px',
                  fontSize: '0.75rem',
                  fontFamily: 'monospace',
                }}
              />
            </div>

            {/* Comment */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', color: '#94a3b8' }}>
                Комментарий
              </label>
              <textarea
                value={editForm.comment || ''}
                onChange={(e) => setEditForm({ ...editForm, comment: e.target.value })}
                rows="2"
                style={{
                  width: '100%',
                  background: '#0b0d10',
                  color: '#e0e3e8',
                  border: '1px solid #334155',
                  borderRadius: '4px',
                  padding: '8px',
                  fontSize: '0.875rem',
                  resize: 'vertical',
                }}
              />
            </div>

            {/* Location */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', color: '#94a3b8' }}>
                Местоположение
              </label>
              <input
                type="text"
                value={editForm.location || ''}
                onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
                placeholder="Этаж 2, корпус А"
                style={{
                  width: '100%',
                  background: '#0b0d10',
                  color: '#e0e3e8',
                  border: '1px solid #334155',
                  borderRadius: '4px',
                  padding: '8px',
                  fontSize: '0.875rem',
                }}
              />
            </div>

            {/* Enabled */}
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem', color: '#94a3b8', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={editForm.enabled !== false}
                  onChange={(e) => setEditForm({ ...editForm, enabled: e.target.checked })}
                  style={{ width: '18px', height: '18px' }}
                />
                Камера включена
              </label>
            </div>

            {/* Audio */}
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem', color: '#94a3b8', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={editForm.audio !== false}
                  onChange={(e) => setEditForm({ ...editForm, audio: e.target.checked })}
                  style={{ width: '18px', height: '18px' }}
                />
                Захватывать аудио
              </label>
            </div>

            {/* Кнопки */}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                className="btn"
                onClick={handleCancel}
                disabled={saving}
              >
                Отмена
              </button>
              <button
                className="btn btn-primary"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Сохранение...' : '💾 Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
