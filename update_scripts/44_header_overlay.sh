#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 44: ШАПКА-ОВЕРЛЕЙ + ЯЧЕЙКИ В ФАЙЛАХ
#  ------------------------------------------------------------
#  Что делает:
#    1. Шапка исчезает через 3 сек после ухода мыши с шапки
#    2. Камеры занимают всё пространство (шапка — оверлей)
#    3. Пустая ячейка вынесена в CameraEmpty.jsx
#
#  ЗАПУСК:  bash update_scripts/44_header_overlay.sh
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
# ЧАСТЬ 1: Header.jsx — автоскрытие по фокусу/ховеру
# ============================================================
echo ""
echo "🔧 Обновляю шапку (автоскрытие по фокусу)..."

cat > "$PROJECT_DIR/frontend/src/components/Header.jsx" << 'HEADER_END'
// ============================================================
//  GRYPHONE — шапка приложения (v44)
//  ------------------------------------------------------------
//  • Шапка-оверлей: налазит на камеры, не занимает место
//  • Исчезает через 3 секунды после ухода мыши с шапки
//  • Пока мышь на шапке — не исчезает
//  • Появляется при движении мыши
// ============================================================
import { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getSets, switchSet } from '../api'

export default function Header() {
  const [sets, setSets] = useState({})
  const [currentSet, setCurrentSet] = useState('')
  const [clock, setClock] = useState('')
  const [visible, setVisible] = useState(true)
  const hideTimerRef = useRef(null)
  const isHoveredRef = useRef(false)
  const location = useLocation()

  const isMonitorPage = location.pathname === '/'
  const isSettingsPage = location.pathname === '/settings'
  const isHelpPage = location.pathname === '/help'

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

  // ИСПРАВЛЕНО (v44): запуск таймера скрытия через 3 секунды
  const startHideTimer = useCallback(() => {
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
    hideTimerRef.current = setTimeout(() => {
      // Скрываем только если мышь НЕ на шапке
      if (!isHoveredRef.current) {
        setVisible(false)
      }
    }, 3000)
  }, [])

  // ИСПРАВЛЕНО (v44): автоскрытие по потере фокуса
  useEffect(() => {
    if (!isMonitorPage) {
      setVisible(true)
      return
    }

    // Показываем шапку при движении мыши
    const showHeader = () => {
      setVisible(true)
      // Запускаем таймер только если мышь не на шапке
      if (!isHoveredRef.current) {
        startHideTimer()
      }
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
  }, [isMonitorPage, startHideTimer])

  // ИСПРАВЛЕНО (v44): мышь вошла на шапку — не скрывать
  const handleMouseEnter = () => {
    isHoveredRef.current = true
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
    setVisible(true)
  }

  // ИСПРАВЛЕНО (v44): мышь ушла с шапки — запускаем таймер 3 сек
  const handleMouseLeave = () => {
    isHoveredRef.current = false
    if (isMonitorPage) {
      startHideTimer()
    }
  }

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
      window.dispatchEvent(new CustomEvent('set-changed', { detail: { setId } }))
    } catch (e) {
      console.error('Ошибка переключения набора:', e)
    }
  }

  return (
    <div
      className={`header ${isMonitorPage && !visible ? 'header-hidden' : ''}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Логотип слева */}
      <div className="header-left">
        <h1 className="header-title">GRYPHONE</h1>
      </div>

      {/* Время по центру */}
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
echo "  ✔ frontend/src/components/Header.jsx (автоскрытие по фокусу)"

# ============================================================
# ЧАСТЬ 2: CameraEmpty.jsx — пустая ячейка в отдельном файле
# ============================================================
echo ""
echo "🔧 Создаю отдельный файл пустой ячейки..."

cat > "$PROJECT_DIR/frontend/src/components/CameraEmpty.jsx" << 'EMPTY_END'
// ============================================================
//  GRYPHONE — пустая ячейка сетки (v44)
//  ------------------------------------------------------------
//  Вынесена в отдельный файл по примеру ContextMenu.jsx.
//  Отображается как слот без камеры: пунктирная рамка
//  и значок «объектив» в центре.
// ============================================================

export default function CameraEmpty({ index }) {
  return (
    <div
      className="camera-empty"
      title={`Пустой слот ${index + 1}`}
    >
      {/* Значок «объектив» создаётся через CSS ::before */}
    </div>
  )
}
EMPTY_END
echo "  ✔ frontend/src/components/CameraEmpty.jsx (пустая ячейка)"

# ============================================================
# ЧАСТЬ 3: Патч MonitorPage.jsx — использовать CameraEmpty
# ============================================================
echo ""
echo "🔧 Обновляю MonitorPage для использования CameraEmpty..."

MONITOR_FILE="$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx"

if [ ! -f "$MONITOR_FILE" ]; then
    echo "⚠️  ВНИМАНИЕ: файл MonitorPage.jsx не найден — пропускаю"
else
    cd "$PROJECT_DIR"
    python << 'PYEOF_PATCH_MONITOR'
from pathlib import Path

file = Path("frontend/src/pages/MonitorPage.jsx")
content = file.read_text(encoding="utf-8")

# Шаг 1: Добавляем импорт CameraEmpty, если его нет
if "CameraEmpty" not in content:
    # Ищем строку импорта CameraCard и добавляем после неё
    if "import CameraCard from" in content:
        content = content.replace(
            "import CameraCard from '../components/CameraCard'",
            "import CameraCard from '../components/CameraCard'\nimport CameraEmpty from '../components/CameraEmpty'"
        )
        print("OK: добавлен импорт CameraEmpty")
    else:
        print("WARNING: не найден импорт CameraCard — добавьте вручную")

# Шаг 2: Заменяем пустые ячейки <div ... camera-empty ... /> на <CameraEmpty />
# Ищем паттерн пустой ячейки и заменяем на компонент
import re

# Паттерн: <div key={`empty-${i}`} className="camera-empty" />
pattern = re.compile(
    r'<div\s+key=\{`empty-\$\{i\}`\}\s+className="camera-empty"\s*/>'
)
if pattern.search(content):
    content = pattern.sub('<CameraEmpty key={`empty-${i}`} index={i} />', content)
    print("OK: заменены пустые ячейки на <CameraEmpty />")
else:
    print("INFO: паттерн пустой ячейки не найден — возможно, уже заменён или другой формат")

# Шаг 3: Убираем класс monitor-page если он добавляет отступ
# (отступ больше не нужен, шапка — оверлей)
content = content.replace('monitor-page', '')

file.write_text(content, encoding="utf-8")
print("OK: MonitorPage.jsx обновлён")
PYEOF_PATCH_MONITOR
fi

# ============================================================
# ЧАСТЬ 4: Патч styles.css — шапка-оверлей, убрать отступ
# ============================================================
echo ""
echo "🔧 Обновляю стили (шапка-оверлей, камеры на всё пространство)..."

STYLES_FILE="$PROJECT_DIR/frontend/src/styles.css"

cd "$PROJECT_DIR"
python << 'PYEOF_PATCH_STYLES'
from pathlib import Path

file = Path("frontend/src/styles.css")
content = file.read_text(encoding="utf-8")

# Шаг 1: Убираем отступ .monitor-page (шапка теперь оверлей)
content = content.replace(".monitor-page {\n  padding-top: 70px;\n}", "")
content = content.replace(".monitor-page {", "/* .monitor-page убран в v44 */\n.monitor-page-removed {")

# Шаг 2: Обновляем .header для оверлея
# Добавляем градиентный фон, чтобы шапка была читаема поверх камер
if ".header-overlay-gradient" not in content:
    content += """

/* ============================================================
   Шапка-оверлей (v44): камеры занимают всё пространство,
   шапка налазит сверху и исчезает через 3 сек после ухода мыши
   ============================================================ */
.header {
  background: linear-gradient(
    to bottom,
    rgba(11, 13, 16, 0.95) 0%,
    rgba(11, 13, 16, 0.85) 70%,
    transparent 100%
  );
  backdrop-filter: blur(8px);
}

/* Контент мониторинга: без отступа, на всё пространство */
.page.monitor-page,
.monitor-page {
  padding-top: 0 !important;
}

/* Сетка камер занимает всю высоту */
.camera-grid-fullspace {
  height: calc(100vh - 16px);
}
"""
    print("OK: добавлены стили шапки-оверлея")

file.write_text(content, encoding="utf-8")
print("OK: styles.css обновлён")
PYEOF_PATCH_STYLES

# ============================================================
# Финальная проверка
# ============================================================
echo ""
echo "🔍 Финальная проверка..."

for f in frontend/src/components/Header.jsx frontend/src/components/CameraEmpty.jsx frontend/src/styles.css; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
  echo "  ✔ $f"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Исправления применены"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что изменено:"
echo "  • Шапка исчезает через 3 сек после ухода мыши с шапки"
echo "  • Пока мышь на шапке — она не исчезает"
echo "  • Камеры занимают всё пространство (шапка — оверлей)"
echo "  • Пустая ячейка вынесена в CameraEmpty.jsx"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 (Ctrl+Shift+R)"