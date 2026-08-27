#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 37: ВОЗВРАТ СПРАВКИ
#  ------------------------------------------------------------
#  Справка была потеряна при переписывании SettingsPage.jsx
#  в скриптах 34/36. Возвращаем её:
#    1. frontend/src/components/Help.jsx — компонент справки
#    2. frontend/src/pages/HelpPage.jsx — отдельная страница
#    3. frontend/src/App.jsx — роут /help
#    4. frontend/src/pages/SettingsPage.jsx — вкладка «Справка»
#
#  Запуск:   bash 37_restore_help.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. Help.jsx — компонент справки
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/Help.jsx" << 'JSXEOF_HELP'
// ============================================================
//  GRYPHONE — компонент «Справка»
//  ------------------------------------------------------------
//  ВОЗВРАЩЕНО (v37): встроенная документация по системе.
// ============================================================

export default function Help() {
  const Section = ({ title, children }) => (
    <div style={{
      background: '#1e293b',
      borderRadius: '8px',
      padding: '16px',
      border: '1px solid #334155',
      marginBottom: '16px',
    }}>
      <h3 style={{ marginBottom: '12px' }}>{title}</h3>
      {children}
    </div>
  )

  const Row = ({ k, v }) => (
    <div style={{
      display: 'flex', gap: '12px', marginBottom: '8px',
      fontSize: '0.875rem', flexWrap: 'wrap',
    }}>
      <span style={{ minWidth: '220px', color: '#94a3b8' }}>{k}</span>
      <span style={{ flex: 1 }}>{v}</span>
    </div>
  )

  return (
    <div>
      <Section title="🖱 Управление камерами">
        <Row k="Двойной клик по камере" v="Открыть полноэкранный режим (основной поток)" />
        <Row k="Двойной клик в полноэкранном режиме" v="Выход из полноэкранного режима" />
        <Row k="Правый клик по камере" v="Контекстное меню: весь экран, вкл/выкл, аудио, местоположение, комментарий" />
        <Row k="Esc" v="Выход из полноэкранного режима" />
        <Row k="Движение мыши в полноэкранном режиме" v="Показать имя камеры и метку MAIN (скрывается через 3 сек)" />
      </Section>

      <Section title="🎥 Потоки (SUB / MAIN)">
        <Row k="В сетке" v="Воспроизводится дополнительный поток (SUB) — экономит ресурсы" />
        <Row k="В полноэкранном режиме" v="Воспроизводится основной поток (MAIN) — максимальное качество" />
        <Row k="Метка SUB/MAIN" v="Левый нижний угол карточки" />
        <Row k="Метка 🔊 / 🔇" v="Правый нижний угол карточки — состояние звука" />
      </Section>

      <Section title="🚦 Статусы камер (кружки)">
        <Row k="🟢 Зелёный" v="Камера онлайн, поток активен" />
        <Row k="🟡 Жёлтый (мигает)" v="Идёт подключение" />
        <Row k="🔴 Красный" v="Камера недоступна или отключена" />
        <Row k="Пустая ячейка" v="Слот без камеры — помечен пунктиром со значком объектива" />
      </Section>

      <Section title="📦 Наборы и сетка">
        <Row k="Селектор в шапке" v="Переключение между наборами (🏢 210, 🏢 403, 🏢 301A, 📦 По умолчанию)" />
        <Row k="Разметка сетки" v="Задаётся в конфиге набора: max_columns × max_rows" />
        <Row k="Расстояние между ячейками" v="2 пикселя" />
        <Row k="Шапка ячейки" v="Прозрачная, поверх видео: имя камеры + кружок статуса" />
      </Section>

      <Section title="📥 Импорт из Excel">
        <Row k="Где" v="Настройки → Наборы → кнопка «📥 Выбрать Excel файл»" />
        <Row k="Обязательные колонки" v="ID, main_url" />
        <Row k="Опциональные колонки" v="name, sub_url, enabled, comment, audio, location" />
        <Row k="Форматы" v=".xlsx (Excel 2007+), .xls (Excel 97-2003)" />
        <Row k="После импорта" v="Наборы создаются автоматически по префиксам ID, нажмите F5" />
      </Section>

      <Section title="📊 Дашборд">
        <Row k="Где" v="Настройки → Дашборд" />
        <Row k="Что показывает" v="Камеры (всего/онлайн/оффлайн), нагрузка CPU/RAM/диск, статусы наборов, проблемные камеры" />
        <Row k="Обновление" v="Автоматически каждые 5 секунд" />
      </Section>

      <Section title="⚙️ Поля камеры">
        <Row k="id" v="Уникальный идентификатор (обязательное)" />
        <Row k="name" v="Отображаемое имя" />
        <Row k="main_url" v="RTSP-ссылка основного потока (обязательное)" />
        <Row k="sub_url" v="RTSP-ссылка дополнительного потока" />
        <Row k="enabled" v="Включена / выключена" />
        <Row k="comment" v="Комментарий" />
        <Row k="audio" v="Звук вкл/выкл (при выкл в FFmpeg добавляется -an)" />
        <Row k="location" v="Местоположение (📍 под именем камеры)" />
      </Section>

      <Section title="⚠️ Устранение проблем">
        <Row k="Серый экран / старый интерфейс" v="Жёсткая перезагрузка: Ctrl+Shift+R" />
        <Row k="401 Unauthorized в логах" v="Неверный логин/пароль в RTSP-ссылке" />
        <Row k="«Хост недоступен»" v="Камера не отвечает по сети (проверьте ping)" />
        <Row k="Видео не появляется после включения" v="Обновлено в v33 — перезапустите бэкенд, если проблема осталась" />
        <Row k="Статус мигает «подключение»" v="Обновлено в v33 — перезапустите бэкенд" />
        <Row k="Поток есть, но видео чёрное" v="Проверьте кодек: поддерживается H.264; звук G.711 перекодируется в AAC" />
      </Section>

      <Section title="🔗 Адреса для диагностики">
        <Row k="/api/dashboard" v="Сводная статистика системы" />
        <Row k="/api/sets" v="Все наборы" />
        <Row k="/api/sets/current" v="Камеры активного набора" />
        <Row k="/api/stream_status" v="Статусы потоков в реальном времени (SSE)" />
        <Row k="/api/ffmpeg_logs" v="Логи FFmpeg по каждому потоку" />
      </Section>
    </div>
  )
}
JSXEOF_HELP
echo "  ✔ frontend/src/components/Help.jsx"

# ============================================================
# 2. HelpPage.jsx — отдельная страница справки
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/HelpPage.jsx" << 'JSXEOF_HELPPAGE'
// ============================================================
//  GRYPHONE — страница справки (/help)
//  ВОЗВРАЩЕНО (v37)
// ============================================================
import Header from '../components/Header'
import Help from '../components/Help'

export default function HelpPage() {
  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">❓ Справка</h1>
      <Help />
    </div>
  )
}
JSXEOF_HELPPAGE
echo "  ✔ frontend/src/pages/HelpPage.jsx"

# ============================================================
# 3. App.jsx — добавлен роут /help
# ============================================================
cat > "$PROJECT_DIR/frontend/src/App.jsx" << 'JSXEOF_APP'
// ============================================================
//  GRYPHONE — главный компонент приложения
//  ВОЗВРАЩЕНО (v37): роут /help
// ============================================================
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MonitorPage from './pages/MonitorPage'
import SettingsPage from './pages/SettingsPage'
import HelpPage from './pages/HelpPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MonitorPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/help" element={<HelpPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
JSXEOF_APP
echo "  ✔ frontend/src/App.jsx (роут /help)"

# ============================================================
# 4. SettingsPage.jsx — вкладка «Справка» + прокрутка
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/SettingsPage.jsx" << 'JSXEOF_SETTINGS'
// ============================================================
//  GRYPHONE — страница настроек
//  ВОЗВРАЩЕНО (v37): вкладка «Справка»
// ============================================================
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import Header from '../components/Header'
import Dashboard from '../components/Dashboard'
import Help from '../components/Help'
import Toasts from '../components/Toasts'
import { getSets, getConfig } from '../api'

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
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />

      <h1 className="page-title">Настройки</h1>

      <div className="tabs">
        <button
          className={`btn ${activeTab === 'dashboard' ? 'btn-primary' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          📊 Дашборд
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
        {/* ВОЗВРАЩЕНО (v37): вкладка Справка */}
        <button
          className={`btn ${activeTab === 'help' ? 'btn-primary' : ''}`}
          onClick={() => setActiveTab('help')}
        >
          ❓ Справка
        </button>
        <Link to="/" className="btn">
          ← Назад к камерам
        </Link>
      </div>

      {activeTab === 'dashboard' && (
        <div className="tab-content">
          <Dashboard />
        </div>
      )}

      {activeTab === 'sets' && (
        <div className="tab-content">
          <h2>Управление наборами камер</h2>

          <div style={{
            marginBottom: '20px', padding: '16px',
            background: '#1e293b', borderRadius: '8px',
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
              background: '#0b0d10', padding: '16px', borderRadius: '8px',
              overflow: 'auto', fontSize: '0.875rem',
            }}>
              {JSON.stringify(configData, null, 2)}
            </pre>
          ) : (
            <p>Загрузка...</p>
          )}
        </div>
      )}

      {/* ВОЗВРАЩЕНО (v37): вкладка Справка */}
      {activeTab === 'help' && (
        <div className="tab-content">
          <Help />
        </div>
      )}

      <Toasts />
    </div>
  )
}
JSXEOF_SETTINGS
echo "  ✔ frontend/src/pages/SettingsPage.jsx (вкладка «Справка»)"

# ------------------------------------------------------------
# Проверка
# ------------------------------------------------------------
for f in frontend/src/components/Help.jsx frontend/src/pages/HelpPage.jsx frontend/src/App.jsx frontend/src/pages/SettingsPage.jsx; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Справка возвращена"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Где теперь справка:"
echo "  • Настройки → вкладка «❓ Справка»"
echo "  • Отдельная страница: http://localhost:5000/help"
echo ""
echo "📖 Разделы справки:"
echo "  • Управление камерами (двойной клик, правый клик, Esc)"
echo "  • Потоки SUB/MAIN"
echo "  • Статусы камер (кружки)"
echo "  • Наборы и сетка"
echo "  • Импорт из Excel"
echo "  • Дашборд"
echo "  • Поля камеры"
echo "  • Устранение проблем"
echo "  • Адреса для диагностики"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 (Ctrl+Shift+R)"