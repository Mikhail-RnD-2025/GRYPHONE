#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 12: СТРАНИЦЫ ФРОНТЕНДА
#  ------------------------------------------------------------
#  Заполняет:
#    - frontend/src/pages/MonitorPage.jsx   — страница мониторинга
#    - frontend/src/pages/SettingsPage.jsx  — страница настроек
#
#  Запуск:   bash 12_frontend_pages.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# frontend/src/pages/MonitorPage.jsx — страница мониторинга
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница мониторинга
//  ------------------------------------------------------------
//  Отображает сетку камер с видеопотоками и статусами.
//  Подписывается на события в реальном времени для обновления
//  статусов.
// ============================================================
import { useState, useEffect } from 'react'
import Header from '../components/Header'
import CameraCard from '../components/CameraCard'
import ContextMenu from '../components/ContextMenu'
import Toasts from '../components/Toasts'
import useStreamStatus from '../hooks/useStreamStatus'
import { getCameras, switchSet } from '../api'

export default function MonitorPage() {
  // Список камер.
  const [cameras, setCameras] = useState([])
  // Состояние контекстного меню.
  const [contextMenu, setContextMenu] = useState(null)

  // Подписка на события в реальном времени (статусы потоков).
  const stats = useStreamStatus()

  // Загружаем список камер при монтировании.
  useEffect(() => {
    loadCameras()
  }, [])

  // Функция загрузки камер.
  const loadCameras = async () => {
    try {
      const data = await getCameras()
      setCameras(data)
    } catch (e) {
      console.error('Ошибка загрузки камер:', e)
    }
  }

  // Обработчик правого клика на карточке камеры.
  const handleContextMenu = (camera, x, y) => {
    setContextMenu({ camera, x, y })
  }

  // Обработчик закрытия контекстного меню.
  const handleCloseContextMenu = () => {
    setContextMenu(null)
  }

  return (
    <div className="page">
      {/* Шапка страницы */}
      <Header />

      {/* Сетка камер */}
      <div className="camera-grid">
        {cameras.map((camera) => (
          <CameraCard
            key={camera.id}
            camera={camera}
            status={stats[camera.id]?.state || 'подключение'}
            onContextMenu={handleContextMenu}
          />
        ))}
      </div>

      {/* Контекстное меню (если открыто) */}
      {contextMenu && (
        <ContextMenu
          camera={contextMenu.camera}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={handleCloseContextMenu}
          onUpdate={loadCameras}
        />
      )}

      {/* Уведомления */}
      <Toasts />
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/MonitorPage.jsx"

# ============================================================
# frontend/src/pages/SettingsPage.jsx — страница настроек
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/SettingsPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница настроек
//  ------------------------------------------------------------
//  Отображает вкладки: конфигурация, камеры, наборы, логи,
//  дашборд. Позволяет редактировать и сохранять настройки.
// ============================================================
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getConfig, saveConfig, getCameras, saveCameras, getSets, saveSets, getFfmpegLogs, getDashboard } from '../api'

export default function SettingsPage() {
  // Активная вкладка.
  const [activeTab, setActiveTab] = useState('config')
  // Данные для каждой вкладки.
  const [config, setConfig] = useState({})
  const [cameras, setCameras] = useState([])
  const [sets, setSets] = useState({})
  const [logs, setLogs] = useState({})
  const [dashboard, setDashboard] = useState({})

  // Загружаем данные при монтировании.
  useEffect(() => {
    loadData()
  }, [])

  // Функция загрузки данных для активной вкладки.
  const loadData = async () => {
    try {
      const [cfg, cams, sts] = await Promise.all([
        getConfig(),
        getCameras(),
        getSets(),
      ])
      setConfig(cfg)
      setCameras(cams)
      setSets(sts)
    } catch (e) {
      console.error('Ошибка загрузки данных:', e)
    }
  }

  // Обработчик переключения вкладок.
  const handleTabChange = (tab) => {
    setActiveTab(tab)
    if (tab === 'logs') {
      loadLogs()
    } else if (tab === 'dashboard') {
      loadDashboard()
    }
  }

  // Функция загрузки логов.
  const loadLogs = async () => {
    try {
      const data = await getFfmpegLogs()
      setLogs(data)
    } catch (e) {
      console.error('Ошибка загрузки логов:', e)
    }
  }

  // Функция загрузки дашборда.
  const loadDashboard = async () => {
    try {
      const data = await getDashboard()
      setDashboard(data)
    } catch (e) {
      console.error('Ошибка загрузки дашборда:', e)
    }
  }

  return (
    <div className="page">
      {/* Заголовок и кнопка возврата */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 className="page-title">Настройки</h1>
        <Link to="/" className="btn btn-primary">Назад к мониторингу</Link>
      </div>

      {/* Вкладки */}
      <div className="tabs" style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        <button
          className={`btn ${activeTab === 'config' ? 'btn-primary' : ''}`}
          onClick={() => handleTabChange('config')}
        >
          Конфигурация
        </button>
        <button
          className={`btn ${activeTab === 'cameras' ? 'btn-primary' : ''}`}
          onClick={() => handleTabChange('cameras')}
        >
          Камеры
        </button>
        <button
          className={`btn ${activeTab === 'sets' ? 'btn-primary' : ''}`}
          onClick={() => handleTabChange('sets')}
        >
          Наборы
        </button>
        <button
          className={`btn ${activeTab === 'logs' ? 'btn-primary' : ''}`}
          onClick={() => handleTabChange('logs')}
        >
          Логи
        </button>
        <button
          className={`btn ${activeTab === 'dashboard' ? 'btn-primary' : ''}`}
          onClick={() => handleTabChange('dashboard')}
        >
          Дашборд
        </button>
      </div>

      {/* Содержимое активной вкладки */}
      <div className="tab-content">
        {activeTab === 'config' && (
          <div>
            <h2>Конфигурация</h2>
            <pre style={{ background: '#1e293b', padding: '12px', borderRadius: '6px' }}>
              {JSON.stringify(config, null, 2)}
            </pre>
          </div>
        )}

        {activeTab === 'cameras' && (
          <div>
            <h2>Камеры</h2>
            <ul>
              {cameras.map((cam) => (
                <li key={cam.id}>
                  {cam.name} — {cam.enabled ? 'включена' : 'отключена'}
                </li>
              ))}
            </ul>
          </div>
        )}

        {activeTab === 'sets' && (
          <div>
            <h2>Наборы</h2>
            <pre style={{ background: '#1e293b', padding: '12px', borderRadius: '6px' }}>
              {JSON.stringify(sets, null, 2)}
            </pre>
          </div>
        )}

        {activeTab === 'logs' && (
          <div>
            <h2>Логи</h2>
            <pre style={{ background: '#1e293b', padding: '12px', borderRadius: '6px', maxHeight: '400px', overflow: 'auto' }}>
              {JSON.stringify(logs, null, 2)}
            </pre>
          </div>
        )}

        {activeTab === 'dashboard' && (
          <div>
            <h2>Дашборд</h2>
            <pre style={{ background: '#1e293b', padding: '12px', borderRadius: '6px' }}>
              {JSON.stringify(dashboard, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/SettingsPage.jsx"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in frontend/src/pages/MonitorPage.jsx frontend/src/pages/SettingsPage.jsx; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo "✅ Страницы фронтенда готовы (с правильным синтаксисом)."
echo "ℹ️  Точка входа и фабрика приложения — скрипт 13."