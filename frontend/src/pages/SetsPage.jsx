// ============================================================
//  GRYPHONE — sets management page
// ============================================================
import { useState, useEffect } from 'react'
import Header from '../components/Header'
import Toasts from '../components/Toasts'
import { getSets, saveSets } from '../api'

export default function SetsPage() {
  const [setsData, setSetsData] = useState(null)
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const sets = await getSets()
      setSetsData(sets)
    } catch (e) {
      console.error('Failed to load sets:', e)
    }
  }

  const handleSaveSets = async () => {
    try {
      await saveSets(setsData)
      if (window.addToast) {
        window.addToast('✅ Sets saved', 'success')
      }
    } catch (e) {
      console.error('Failed to save sets:', e)
      if (window.addToast) {
        window.addToast('❌ Failed to save sets', 'error')
      }
    }
  }

  const handleExcelImport = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    if (!file.name.endsWith('.xls') && !file.name.endsWith('.xlsx')) {
      if (window.addToast) {
        window.addToast('❌ Invalid format. Use .xlsx or .xls', 'error')
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
          window.addToast(`✅ ${result.message}. Press F5`, 'success')
        }
        await loadData()
      } else {
        if (window.addToast) {
          window.addToast(`❌ ${result.message}`, 'error')
        }
      }
    } catch (e) {
      if (window.addToast) {
        window.addToast(`❌ Import error: ${e.message}`, 'error')
      }
    } finally {
      setImporting(false)
      event.target.value = ''
    }
  }

  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">📦 Управление наборами</h1>

      <div className="tab-content">
        <div style={{
          marginBottom: '20px', padding: '16px',
          background: '#1e293b', borderRadius: '8px',
          border: '1px solid #334155',
        }}>
          <h3 style={{ marginBottom: '12px' }}>📥 Import from Excel</h3>
          <p style={{ color: '#94a3b8', marginBottom: '12px' }}>
            Required columns: <strong>ID</strong>, <strong>main_url</strong>.
            Optional: name, sub_url, enabled, comment, audio, location.
          </p>
          <label className="btn btn-primary" style={{ cursor: 'pointer' }}>
            {importing ? '⏳ Loading...' : '📥 Choose Excel file'}
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
            <p>Active set: <strong>{setsData.default_set || 'not selected'}</strong></p>
            <p>Total sets: <strong>{Object.keys(setsData.sets || {}).length}</strong></p>
            <div style={{ marginTop: '16px' }}>
              <button className="btn btn-primary" onClick={handleSaveSets}>
                💾 Save sets
              </button>
            </div>
          </div>
        ) : (
          <p>Loading...</p>
        )}
      </div>

      <Toasts />
    </div>
  )
}
