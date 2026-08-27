// ============================================================
//  GRYPHONE — settings page (v48)
//  Dashboard moved to /status, only config remains here
// ============================================================
import { useState, useEffect } from 'react'
import Header from '../components/Header'
import Toasts from '../components/Toasts'
import { getConfig } from '../api'

export default function SettingsPage() {
  const [configData, setConfigData] = useState(null)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const config = await getConfig()
      setConfigData(config)
    } catch (e) {
      console.error('Failed to load config:', e)
    }
  }

  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">⚙️ Настройки</h1>
      <div className="tab-content">
        <h2>Конфигурация системы</h2>
        {configData ? (
          <pre style={{
            background: '#0b0d10', padding: '16px', borderRadius: '8px',
            overflow: 'auto', fontSize: '0.875rem', maxHeight: '600px',
          }}>
            {JSON.stringify(configData, null, 2)}
          </pre>
        ) : (
          <p>Загрузка...</p>
        )}
      </div>
      <Toasts />
    </div>
  )
}
