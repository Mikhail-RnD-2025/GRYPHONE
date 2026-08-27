// ============================================================
//  GRYPHONE — страница настроек
//  ИСПРАВЛЕНО (v41):
//  • Шапки разделов вынесены из прокручиваемой области
//  • Используется переиспользуемый компонент SectionHeader
//  • Шапка всегда видна, контент прокручивается отдельно
// ============================================================
import { useState, useEffect } from 'react'
import Header from '../components/Header'
import Dashboard from '../components/Dashboard'
import Help from '../components/Help'
import CamerasEditor from '../components/CamerasEditor'
import SectionHeader from '../components/SectionHeader'
import Toasts from '../components/Toasts'
import { getSets, saveSets, getConfig } from '../api'

// Словарь заголовков для каждой вкладки
const SECTION_INFO = {
  dashboard: {
    icon: '📊',
    title: 'Дашборд',
    description: 'Общая статистика системы и камер',
  },
  cameras: {
    icon: '📹',
    title: 'Редактор камер',
    description: 'Управление камерами, импорт и экспорт конфигурации',
  },
  sets: {
    icon: '📦',
    title: 'Управление наборами камер',
    description: 'Группировка камер по наборам, импорт из Excel',
  },
  config: {
    icon: '⚙️',
    title: 'Конфигурация системы',
    description: 'Просмотр текущих настроек приложения',
  },
  help: {
    icon: '❓',
    title: 'Справка',
    description: 'Документация и руководство пользователя',
  },
}

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

  // Получаем информацию о текущем разделе
  const currentSection = SECTION_INFO[activeTab] || SECTION_INFO.dashboard

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

      {/* Вкладки */}
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

      {/* ИСПРАВЛЕНО (v41): шапка раздела вынесена из прокрутки */}
      <SectionHeader
        icon={currentSection.icon}
        title={currentSection.title}
        description={currentSection.description}
      />

      {/* Прокручиваемый контент — без шапки */}
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
            <CamerasEditor />
          </div>
        )}

        {activeTab === 'sets' && (
          <div className="tab-content">
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
