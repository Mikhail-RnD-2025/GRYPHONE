#!/bin/sh
# ============================================================================
# 83. update_scripts/83_fix_header_comprehensive.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Комплексное исправление шапки:
#   1. Удаляет ВСЕ дублирующиеся блоки .header из styles.css
#   2. Создаёт один чистый блок с правильными стилями
#   3. Исправляет логику автоскрытия в Header.jsx для всех страниц
#   4. Убирает pointer-events: none в hidden состоянии (ломал меню)
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./83_fix_header_comprehensive.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "83: Комплексное исправление шапки (CSS + JSX)"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

CSS_FILE="frontend/src/styles.css"
HEADER_FILE="frontend/src/components/Header.jsx"

if [ ! -f "$CSS_FILE" ]; then
    echo "ОШИБКА: не найден $CSS_FILE" >&2; exit 1
fi
if [ ! -f "$HEADER_FILE" ]; then
    echo "ОШИБКА: не найден $HEADER_FILE" >&2; exit 1
fi

# --- Детект Python ---
_detect_python() {
    for cmd in python python3 py; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" --version >/dev/null 2>&1; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}
PYTHON_CMD="$(_detect_python || true)"
if [ -z "$PYTHON_CMD" ]; then
    echo "ОШИБКА: не найден Python" >&2; exit 1
fi
echo "Python: $PYTHON_CMD"

# ============================================================================
# ШАГ 1: Резервные копии
# ============================================================================
echo ""
echo "--- ШАГ 1: Резервные копии ---"
cp "$CSS_FILE" "$CSS_FILE.bak-83"
cp "$HEADER_FILE" "$HEADER_FILE.bak-83"
echo "  [BAK] $CSS_FILE.bak-83"
echo "  [BAK] $HEADER_FILE.bak-83"

# ============================================================================
# ШАГ 2: Очистка и пересоздание стилей .header
# ============================================================================
echo ""
echo "--- ШАГ 2: Очистка стилей ---"

"$PYTHON_CMD" - "$CSS_FILE" << 'PYEOF'
import sys
import re
from pathlib import Path

css_file = Path(sys.argv[1])
content = css_file.read_text(encoding="utf-8")

# Удаляем ВСЕ блоки .header и связанные с ними
patterns_to_remove = [
    r'\.header\s*\{[^}]*\}',
    r'\.header-hidden\s*\{[^}]*\}',
    r'\.header-trigger\s*\{[^}]*\}',
    r'\.header-left\s*\{[^}]*\}',
    r'\.header-center\s*\{[^}]*\}',
    r'\.header-right\s*\{[^}]*\}',
    r'\.header-title\s*\{[^}]*\}',
    r'\.header-clock\s*\{[^}]*\}',
    r'\.set-selector\s*\{[^}]*\}',
    r'\.set-selector-right\s*\{[^}]*\}',
    r'\.header:hover\s*\{[^}]*\}',
    r'\.set-selector:hover\s*\{[^}]*\}',
    r'\.set-selector:focus\s*\{[^}]*\}',
]

removed_count = 0
for pattern in patterns_to_remove:
    matches = re.findall(pattern, content, re.DOTALL)
    if matches:
        content = re.sub(pattern, '', content, flags=re.DOTALL)
        removed_count += len(matches)

print(f"  [CLEAN] Удалено {removed_count} блоков стилей header/set-selector")

# Удаляем также секции с заголовками о шапке
content = re.sub(r'/\*[\s\S]*?(?:Шапка|header|Header|PATCH-82)[\s\S]*?\*/\s*', '', content, flags=re.IGNORECASE)

# Чистый блок стилей для шапки
new_styles = """
/* ============================================================
   Шапка приложения (PATCH-83: единый блок)
   - Фиксированная (position: fixed) на всех страницах
   - Наползает на контент
   - Автоскрытие через 2 сек бездействия
   - pointer-events НЕ отключается в hidden (иначе меню ломается)
   ============================================================ */

.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(51, 65, 85, 0.5);
  transition: transform 0.3s ease, opacity 0.3s ease;
  height: 56px;
}

.header-hidden {
  transform: translateY(-100%);
  opacity: 0;
  /* ВАЖНО: НЕ pointer-events: none - иначе выпадающее меню не работает! */
}

.header-trigger {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 20px;
  z-index: 999;
  background: transparent;
  pointer-events: auto;
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  min-width: 0;
}

.header-center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}

.header-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s ease;
  padding: 4px 8px;
  border-radius: 4px;
}

.header-title:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  transform: scale(1.02);
}

.header-title:active {
  transform: scale(0.98);
}

.header-title.fullscreen-active {
  color: #10b981;
  text-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
}

.header-clock {
  font-size: 0.875rem;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
}

.set-selector-right {
  padding: 6px 10px;
  background: #1e293b;
  color: #e2e8f0;
  border: 1px solid #475569;
  border-radius: 6px;
  font-size: 0.8125rem;
  cursor: pointer;
  transition: border-color 0.2s;
  max-width: 180px;
}

.set-selector-right:hover {
  border-color: #64748b;
}

.set-selector-right:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

/* Убираем отступы у контента - шапка наползает */
.page {
  padding-top: 0 !important;
  margin-top: 0 !important;
}
"""

# Добавляем чистые стили в конец файла
content += "\n" + new_styles

css_file.write_text(content, encoding="utf-8")
print("  [OK] Создан единый чистый блок стилей .header")
PYEOF

# ============================================================================
# ШАГ 3: Исправление Header.jsx
# ============================================================================
echo ""
echo "--- ШАГ 3: Исправление Header.jsx ---"

"$PYTHON_CMD" - "$HEADER_FILE" << 'PYEOF'
import sys
from pathlib import Path

header_file = Path(sys.argv[1])

# Полностью переписываем Header.jsx с правильной логикой
new_content = '''import { useState, useEffect, useRef, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import { getSets, switchSet } from '../api'
import HamburgerMenu from './HamburgerMenu'

export default function Header() {
  const [sets, setSets] = useState({})
  const [currentSet, setCurrentSet] = useState('')
  const [clock, setClock] = useState('')
  const [visible, setVisible] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const hideTimerRef = useRef(null)
  const isHoveredRef = useRef(false)
  const location = useLocation()
  const isMonitorPage = location.pathname === '/'

  useEffect(() => { loadSets() }, [])

  useEffect(() => {
    const updateClock = () => {
      const now = new Date()
      setClock(now.toLocaleTimeString('ru-RU', {
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      }))
    }
    updateClock()
    const interval = setInterval(updateClock, 1000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  const toggleFullscreen = useCallback(async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen()
      } else {
        await document.exitFullscreen()
      }
    } catch (err) {
      console.error('Fullscreen error:', err)
    }
  }, [])

  // PATCH-83: Автоскрытие на ВСЕХ страницах
  useEffect(() => {
    setVisible(false)
  }, [location.pathname])

  const cancelHide = () => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current)
      hideTimerRef.current = null
    }
  }

  const scheduleHide = () => {
    cancelHide()
    hideTimerRef.current = setTimeout(() => {
      if (!isHoveredRef.current) setVisible(false)
    }, 2000)
  }

  const handleMouseEnter = () => {
    isHoveredRef.current = true
    cancelHide()
    setVisible(true)
  }

  const handleMouseLeave = () => {
    isHoveredRef.current = false
    scheduleHide()
  }

  useEffect(() => {
    return () => {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
    }
  }, [])

  const loadSets = async () => {
    try {
      const data = await getSets()
      setSets(data.sets || {})
      setCurrentSet(data.default_set || '')
    } catch (e) {
      console.error('Failed to load sets:', e)
    }
  }

  const handleSetChange = async (e) => {
    const setId = e.target.value
    setCurrentSet(setId)
    try {
      await switchSet(setId)
      window.dispatchEvent(new CustomEvent('set-changed', { detail: { setId } }))
    } catch (e) {
      console.error('Failed to switch set:', e)
    }
  }

  return (
    <>
      {/* PATCH-83: trigger на ВСЕХ страницах */}
      <div className="header-trigger" onMouseEnter={handleMouseEnter} />

      <div
        className={`header ${!visible ? 'header-hidden' : ''}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <div className="header-left">
          <h1
            className={`header-title ${isFullscreen ? 'fullscreen-active' : ''}`}
            onClick={toggleFullscreen}
            title={isFullscreen ? 'Выйти из полноэкранного режима' : 'Полноэкранный режим'}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                toggleFullscreen()
              }
            }}
          >
            GRYPHONE-VISION
          </h1>
        </div>

        <div className="header-center">
          <span className="header-clock">{clock}</span>
        </div>

        <div className="header-right">
          {/* Селектор наборов только на главной */}
          {isMonitorPage && Object.keys(sets).length > 0 && (
            <select
              className="set-selector-right"
              value={currentSet}
              onChange={handleSetChange}
              title="Выбор набора"
            >
              {Object.entries(sets).map(([id, set]) => (
                <option key={id} value={id}>{set.name}</option>
              ))}
            </select>
          )}
          <HamburgerMenu />
        </div>
      </div>
    </>
  )
}
'''

header_file.write_text(new_content, encoding="utf-8")
print("  [FIXED] Header.jsx переписан с правильной логикой автоскрытия")
PYEOF

echo ""
echo "============================================================================"
echo "Готово. Резервные копии: *.bak-83"
echo ""
echo "Обязательно пересоберите фронтенд:"
echo "  cd $PROJECT_ROOT/frontend"
echo "  npm run build"
echo ""
echo "Что исправлено:"
echo "  • Удалены ВСЕ дубликаты стилей .header из CSS (v42, v43, v44, v45, PATCH-82)"
echo "  • Создан один чистый блок с правильными стилями"
echo "  • Убран pointer-events: none в hidden состоянии (это ломало меню!)"
echo "  • Логика автоскрытия работает на ВСЕХ страницах"
echo "  • header-trigger активен на ВСЕХ страницах"
echo "============================================================================"