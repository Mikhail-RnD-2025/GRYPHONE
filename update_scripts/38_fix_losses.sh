#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 38: ВОССТАНОВЛЕНИЕ ПОТЕРЬ
#  ------------------------------------------------------------
#  • Удаляет дублирующий роут /api/dashboard из api.py
#  • Проверяет наличие /api/dashboard в dashboard.py
#  • Гарантирует функцию saveSets в frontend/src/api.js
#  • Восстанавливает кнопку «Сохранить наборы» в SettingsPage
#
#  ЗАПУСК:  bash update_scripts/38_fix_losses.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Умное определение корня проекта:
# если скрипт лежит в корне (там есть main.py) — корень = SCRIPT_DIR,
# иначе (скрипт в update_scripts/) — корень = родительская директория.
if [ -f "$SCRIPT_DIR/main.py" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
else
    PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
fi

echo "📁 Корень проекта: $PROJECT_DIR"

# КРИТИЧНО: переходим в корень проекта, чтобы относительные
# пути в Python-блоках резолвились правильно.
cd "$PROJECT_DIR"
echo "📂 Рабочая директория: $(pwd)"

# ============================================================
# НАДЁЖНОЕ ОПРЕДЕЛЕНИЕ PYTHON (без Windows Store)
# ============================================================
_detect_python() {
    local cmd
    for cmd in python python3 py; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" --version >/dev/null 2>&1; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    if command -v py >/dev/null 2>&1; then
        if py -3 --version >/dev/null 2>&1; then
            echo "py -3"
            return 0
        fi
    fi
    return 1
}

PYTHON_CMD="$(_detect_python || true)"

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ ОШИБКА: не найден работающий интерпретатор Python."
    echo "   Установите Python с сайта python.org и добавьте в PATH."
    exit 1
fi

read -ra PYCMD <<< "$PYTHON_CMD"
echo "✅ Найден интерпретатор: ${PYCMD[*]} ($(${PYCMD[@]} --version 2>&1))"

# ============================================================
# ПРОВЕРКА ИСХОДНЫХ ФАЙЛОВ
# ============================================================
if [ ! -f "$PROJECT_DIR/app/routes/api.py" ]; then
    echo "❌ ОШИБКА: файл app/routes/api.py не найден!"
    echo "   Текущая директория: $(pwd)"
    exit 1
fi
echo "  ✔ Файл app/routes/api.py найден"

# ============================================================
# ЧАСТЬ 1: УДАЛЕНИЕ ДУБЛЯ /api/dashboard ИЗ api.py
# ============================================================
echo ""
echo "🔧 Удаляю дублирующий роут /api/dashboard из api.py..."

"${PYCMD[@]}" << 'PYEOF_REMOVE_DASHBOARD'
from pathlib import Path

api_path = Path("app/routes/api.py")
if not api_path.exists():
    print("File not found:", api_path.absolute())
    raise SystemExit(1)

lines = api_path.read_text(encoding="utf-8").split("\n")

# Ищем строку с /api/dashboard
route_idx = None
for idx, line in enumerate(lines):
    if "/api/dashboard" in line and "dashboard_legacy" not in line:
        # Откатываемся к началу декоратора @app.route
        j = idx
        while j >= 0 and "@app.route" not in lines[j]:
            j -= 1
        route_idx = j if j >= 0 else idx
        break

if route_idx is None:
    print("INFO: роут /api/dashboard в api.py не найден — удалять нечего.")
    raise SystemExit(0)

start = route_idx
# Подхватываем комментарии непосредственно над декоратором
hdr = start - 1
while hdr >= 0 and lines[hdr].strip() != "" and lines[hdr].strip().startswith("#"):
    start = hdr
    hdr -= 1

# Ищем строку def после декоратора
def_idx = start
while def_idx < len(lines) and not lines[def_idx].strip().startswith("def "):
    def_idx += 1

if def_idx >= len(lines):
    print("ERROR: не удалось найти тело функции — блок не удалён.")
    raise SystemExit(1)

def_line = lines[def_idx]
def_indent = len(def_line) - len(def_line.lstrip())

# Тело функции: строки с отступом больше, чем у def
end = def_idx + 1
while end < len(lines):
    line = lines[end]
    if line.strip() == "":
        end += 1
        continue
    cur_indent = len(line) - len(line.lstrip())
    if cur_indent > def_indent:
        end += 1
    else:
        break

new_lines = lines[:start] + lines[end:]
api_path.write_text("\n".join(new_lines), encoding="utf-8")
print(f"OK: удалён блок /api/dashboard из api.py (строки {start + 1}-{end}).")
PYEOF_REMOVE_DASHBOARD

# ============================================================
# ЧАСТЬ 2: ПРОВЕРКА, ЧТО dashboard.py СОДЕРЖИТ /api/dashboard
# ============================================================
echo ""
echo "🔍 Проверяю наличие /api/dashboard в dashboard.py..."

if [ -f "$PROJECT_DIR/app/routes/dashboard.py" ]; then
    if grep -q '/api/dashboard' "$PROJECT_DIR/app/routes/dashboard.py"; then
        echo "  ✔ dashboard.py содержит /api/dashboard"
    else
        echo "⚠️  ВНИМАНИЕ: dashboard.py существует, но не содержит /api/dashboard."
    fi
else
    echo "⚠️  ВНИМАНИЕ: файл app/routes/dashboard.py не найден."
    echo "   Убедитесь, что скрипт 36 (улучшенный дашборд) был применён."
fi

# ============================================================
# ЧАСТЬ 3: ГАРАНТИЯ НАЛИЧИЯ saveSets В api.js
# ============================================================
echo ""
echo "🔍 Проверяю наличие saveSets в frontend/src/api.js..."

API_JS="$PROJECT_DIR/frontend/src/api.js"
if [ -f "$API_JS" ]; then
    if grep -q "saveSets" "$API_JS"; then
        echo "  ✔ saveSets уже есть в api.js"
    else
        echo "" >> "$API_JS"
        echo "export function saveSets(data) {" >> "$API_JS"
        echo "  return request('/sets/save', { method: 'POST', body: JSON.stringify(data) })" >> "$API_JS"
        echo "}" >> "$API_JS"
        echo "✅ Добавлена функция saveSets в api.js"
    fi
else
    echo "⚠️  ВНИМАНИЕ: файл frontend/src/api.js не найден."
fi

# ============================================================
# ЧАСТЬ 4: ВОССТАНОВЛЕНИЕ SettingsPage.jsx
# ============================================================
echo ""
echo "🔧 Восстанавливаю кнопку «Сохранить наборы» в SettingsPage..."

mkdir -p "$PROJECT_DIR/frontend/src/pages"

cat > "$PROJECT_DIR/frontend/src/pages/SettingsPage.jsx" << 'SETTINGS_JSX_END'
// ============================================================
//  GRYPHONE — страница настроек
//  ВОССТАНОВЛЕНО (v38): кнопка «Сохранить наборы»
// ============================================================
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import Header from '../components/Header'
import Dashboard from '../components/Dashboard'
import Help from '../components/Help'
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

  // ВОССТАНОВЛЕНО (v38): сохранение наборов
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

              {/* ВОССТАНОВЛЕНО (v38): кнопка сохранения наборов */}
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

      {activeTab === 'help' && (
        <div className="tab-content">
          <Help />
        </div>
      )}

      <Toasts />
    </div>
  )
}
SETTINGS_JSX_END
echo "  ✔ frontend/src/pages/SettingsPage.jsx (кнопка «Сохранить наборы»)"

# ============================================================
# ФИНАЛЬНАЯ ПРОВЕРКА
# ============================================================
echo ""
echo "🔍 Финальная проверка..."

if [ ! -s "$PROJECT_DIR/frontend/src/pages/SettingsPage.jsx" ]; then
    echo "❌ ОШИБКА: файл SettingsPage.jsx пуст или не создан!" >&2
    exit 1
fi
echo "  ✔ SettingsPage.jsx"

if grep -q '"/api/dashboard"' "$PROJECT_DIR/app/routes/api.py" 2>/dev/null; then
    echo "⚠️  ВНИМАНИЕ: в api.py всё ещё есть /api/dashboard."
    echo "   Возможно, формат файла отличается от ожидаемого."
    echo "   Удалите блок вручную."
else
    echo "  ✔ В api.py нет дублирующего /api/dashboard"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Потери восстановлены"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 (Ctrl+Shift+R)"