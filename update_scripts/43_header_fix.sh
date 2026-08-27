#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 43: ИСПРАВЛЕНИЕ ШАПКИ (перегенерировано)
#  ------------------------------------------------------------
#  Что исправляет:
#    1. Переключение наборов (событие сет-чангед)
#    2. Время по центру шапки (абсолютное позиционирование)
#    3. Справа: наборы → навигация → справка
#    4. Автоскрытие шапки на мониторинге через 3 сек бездействия
#
#  ЗАПУСК:  bash update_scripts/43_header_fix.sh
#  ПОСЛЕ:   bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Умное определение корня проекта
if [ -f "$SCRIPT_DIR/main.py" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
else
    PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
fi

echo "📁 Корень проекта: $PROJECT_DIR"
cd "$PROJECT_DIR"
echo "📂 Рабочая директория: $(pwd)"

# ============================================================
# Надёжное определение Python (без Windows Store)
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
# ЧАСТЬ 1: Header.jsx — правильная компоновка
# ============================================================
echo ""
echo "🔧 Обновляю шапку приложения (компоновка + событие)..."

mkdir -p "$PROJECT_DIR/frontend/src/components"

cat > "$PROJECT_DIR/frontend/src/components/Header.jsx" << 'HEADER_END'
// ============================================================
//  GRYPHONE — шапка приложения
//  ИСПРАВЛЕНО (v43):
//  • Время по центру (абсолютное позиционирование)
//  • Справа: наборы → навигация → справка
//  • Переключение наборов диспатчит событие сет-чангед
//  • Автоскрытие на мониторинге через 3 сек бездействия мыши
// ============================================================
import { useState, useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getSets, switchSet } from '../api'

export default function Header() {
  const [sets, setSets] = useState({})
  const [currentSet, setCurrentSet] = useState('')
  const [clock, setClock] = useState('')
  const [visible, setVisible] = useState(true)
  const hideTimerRef = useRef(null)
  const location = useLocation()

  const isMonitorPage = location.pathname === '/'
  const isSettingsPage = location.pathname === '/settings'
  const isHelpPage = location.pathname === '/help'

  useEffect(() => {
    loadSets()
  }, [])

  // Часы обновляются каждую секунду
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

  // Автоскрытие только на мониторинге
  useEffect(() => {
    if (!isMonitorPage) {
      setVisible(true)
      return
    }
    const showHeader = () => {
      setVisible(true)
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
      hideTimerRef.current = setTimeout(() => setVisible(false), 3000)
    }
    showHeader()
    window.addEventListener('mousemove', showHeader)
    window.addEventListener('mousedown', showHeader)
    window.addEventListener('touchstart', showHeader)
    return () => {
      window.removeEventListener('mousemove', showHeader)
      window.removeEventListener('mousedown', showHeader)
      window.removeEventListener('touchstart', showHeader)
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
    }
  }, [isMonitorPage])

  const loadSets = async () => {
    try {
      const data = await getSets()
      setSets(data.sets || {})
      setCurrentSet(data.default_set || '')
    } catch (e) {
      console.error('Ошибка загрузки наборов:', e)
    }
  }

  // ИСПРАВЛЕНО (v43): после переключения диспатчим событие
  const handleSetChange = async (e) => {
    const setId = e.target.value
    setCurrentSet(setId)
    try {
      await switchSet(setId)
      window.dispatchEvent(new CustomEvent('set-changed', { detail: { setId } }))
    } catch (e) {
      console.error('Ошибка переключения набора:', e)
    }
  }

  return (
    <div className={`header ${isMonitorPage && !visible ? 'header-hidden' : ''}`}>
      {/* Логотип слева */}
      <div className="header-left">
        <h1 className="header-title">GRYPHONE</h1>
      </div>

      {/* Время по центру (абсолютно) */}
      <div className="header-center">
        <span className="header-clock">{clock}</span>
      </div>

      {/* Справа: наборы → навигация → справка */}
      <div className="header-right">
        {isMonitorPage && Object.keys(sets).length > 0 && (
          <select
            className="set-selector"
            value={currentSet}
            onChange={handleSetChange}
            title="Выбор набора"
          >
            {Object.entries(sets).map(([id, set]) => (
              <option key={id} value={id}>
                {set.name}
              </option>
            ))}
          </select>
        )}

        {(isSettingsPage || isHelpPage) && (
          <Link to="/" className="header-btn" title="Назад к камерам">
            ← Камеры
          </Link>
        )}

        {(isMonitorPage || isHelpPage) && (
          <Link to="/settings" className="header-btn" title="Настройки">
            ⚙️
          </Link>
        )}

        {!isHelpPage && (
          <Link to="/help" className="header-btn" title="Справка">
            ❓
          </Link>
        )}
      </div>
    </div>
  )
}
HEADER_END
echo "  ✔ frontend/src/components/Header.jsx (компоновка + событие)"

# ============================================================
# ЧАСТЬ 2: Патч MonitorPage.jsx — слушатель сет-чангед
# ============================================================
echo ""
echo "🔧 Добавляю слушатель смены набора в MonitorPage..."

MONITOR_FILE="$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx"

if [ ! -f "$MONITOR_FILE" ]; then
    echo "⚠️  ВНИМАНИЕ: файл MonitorPage.jsx не найден — пропускаю"
else
    "${PYCMD[@]}" << 'PYEOF_PATCH'
from pathlib import Path

file = Path("frontend/src/pages/MonitorPage.jsx")
content = file.read_text(encoding="utf-8")

if "set-changed" in content:
    print("INFO: слушатель set-changed уже есть — пропускаю")
    raise SystemExit(0)

new_block = """
  // ИСПРАВЛЕНО (v43): слушаем событие смены набора из Header
  useEffect(() => {
    const handleSetChanged = () => {
      loadCurrentSet()
    }
    window.addEventListener('set-changed', handleSetChanged)
    return () => {
      window.removeEventListener('set-changed', handleSetChanged)
    }
  }, [])"""

# Ищем блок с загрузкой текущего набора и добавляем после него слушатель
import re

# Вариант 1: стандартный формат
pattern1 = re.compile(
    r'(useEffect\(\(\)\s*=>\s*\{\s*\n\s*loadCurrentSet\(\)\s*\n\s*\},\s*\[\]\))'
)
match1 = pattern1.search(content)

if match1:
    insert_pos = match1.end()
    content = content[:insert_pos] + new_block + content[insert_pos:]
    file.write_text(content, encoding="utf-8")
    print("OK: добавлен слушатель set-changed в MonitorPage.jsx")
    raise SystemExit(0)

# Вариант 2: любой первый юзЕффецт с лоадКуррентСет
pattern2 = re.compile(r'(useEffect\([^)]*loadCurrentSet[^)]*\[\]\))', re.DOTALL)
match2 = pattern2.search(content)

if match2:
    insert_pos = match2.end()
    content = content[:insert_pos] + new_block + content[insert_pos:]
    file.write_text(content, encoding="utf-8")
    print("OK: добавлен слушатель set-changed (вариант 2)")
    raise SystemExit(0)

# Вариант 3: добавляем после первого юзЕффецт
pattern3 = re.compile(r'(useEffect\(\(\)\s*=>\s*\{[^}]*\},\s*\[\]\))', re.DOTALL)
match3 = pattern3.search(content)

if match3:
    insert_pos = match3.end()
    content = content[:insert_pos] + new_block + content[insert_pos:]
    file.write_text(content, encoding="utf-8")
    print("OK: добавлен слушатель set-changed (вариант 3)")
    raise SystemExit(0)

print("WARNING: не удалось автоматически добавить слушатель")
print("Добавьте вручную в MonitorPage.jsx после первого юзЕффецт:")
print(new_block)
PYEOF_PATCH
fi

# ============================================================
# ЧАСТЬ 3: Стили компоновки шапки
# ============================================================
echo ""
echo "🔧 Добавляю стили компоновки шапки..."

STYLES_FILE="$PROJECT_DIR/frontend/src/styles.css"

if grep -q '.header-center' "$STYLES_FILE" 2>/dev/null; then
    echo "  ℹ️  Стили компоновки уже есть — пропускаю"
else
    cat >> "$STYLES_FILE" << 'STYLES_END'

/* ============================================================
   Компоновка шапки (v43)
   ============================================================ */

/* Шапка: три зоны — лево, центр, право */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  height: 56px;
  position: relative;
}

/* Левая часть: логотип */
.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  min-width: 0;
}

/* Центральная часть: время (абсолютно по центру) */
.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  pointer-events: none;
}

.header-clock {
  font-size: 1rem;
  font-weight: 500;
  color: #e0e3e8;
  font-family: monospace;
}

/* Правая часть: наборы → навигация → справка */
.header-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
}

/* Кнопки в шапке */
.header-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 10px;
  background: #334155;
  color: #e0e3e8;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.875rem;
  transition: background 0.2s ease;
  white-space: nowrap;
}

.header-btn:hover {
  background: #475569;
}

/* Заголовок в шапке */
.header-title {
  font-size: 1.25rem;
  color: #2563eb;
  margin: 0;
  white-space: nowrap;
}
STYLES_END
    echo "  ✔ Стили компоновки добавлены в styles.css"
fi

# ============================================================
# Финальная проверка
# ============================================================
echo ""
echo "🔍 Финальная проверка..."

for f in frontend/src/components/Header.jsx frontend/src/styles.css; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
  echo "  ✔ $f"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Шапка исправлена"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что исправлено:"
echo "  • Переключение наборов работает (событие сет-чангед)"
echo "  • Время точно по центру (абсолютное позиционирование)"
echo "  • Справа: наборы → навигация → справка"
echo "  • Автоскрытие на мониторинге через 3 сек бездействия"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 (Ctrl+Shift+R)"sh