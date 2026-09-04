#!/bin/sh
# ============================================================================
# 99. update_scripts/99_rollback_to_pre81.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Откат к состоянию ДО патча 81 (когда всё работало).
#   Восстанавливает Header.jsx и styles.css из рабочих версий.
#
# ЧТО ВОССТАНАВЛИВАЕТСЯ:
#   • Header.jsx: автоскрытие ТОЛЬКО на главной, header-trigger ТОЛЬКО на главной
#   • styles.css: убираем все position:fixed для шапки на всех страницах
#   • Логотип: "GRYPHONE" (не "GRYPHONE-VISION")
#   • Селектор наборов: слева в header-left
#
# ЗАПУСК: ./99_rollback_to_pre81.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "99: Откат к состоянию до патча 81"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

HEADER_FILE="frontend/src/components/Header.jsx"
CSS_FILE="frontend/src/styles.css"

# ============================================================================
# ШАГ 1: Резервные копии текущего состояния
# ============================================================================
echo ""
echo "--- ШАГ 1: Резервные копии текущего состояния ---"
cp "$HEADER_FILE" "$HEADER_FILE.bak-99-before"
cp "$CSS_FILE" "$CSS_FILE.bak-99-before"
echo "  [BAK] $HEADER_FILE.bak-99-before"
echo "  [BAK] $CSS_FILE.bak-99-before"

# ============================================================================
# ШАГ 2: Восстановление Header.jsx (версия из GitHub - до патча 81)
# ============================================================================
echo ""
echo "--- ШАГ 2: Восстановление Header.jsx ---"

cat > "$HEADER_FILE" << 'HEADERJSX'
// ============================================================
// GRYPHONE-VISION — application header (v48)
// ------------------------------------------------------------
// Left: logo
// Center: clock
// Right: hamburger menu (all navigation moved there)
// ============================================================

import { useState, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { getSets, switchSet } from '../api'
import HamburgerMenu from './HamburgerMenu'

export default function Header() {
  const [sets, setSets] = useState({})
  const [currentSet, setCurrentSet] = useState('')
  const [clock, setClock] = useState('')
  const [visible, setVisible] = useState(true)
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

  // Auto-hide logic (only on monitor page)
  useEffect(() => {
    if (!isMonitorPage) {
      setVisible(true)
      return
    }
    setVisible(false)
  }, [isMonitorPage])

  const cancelHide = () => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current)
      hideTimerRef.current = null
    }
  }

  const scheduleHide = () => {
    if (!isMonitorPage) return
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
    if (isMonitorPage) scheduleHide()
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
      {isMonitorPage && (
        <div className="header-trigger" onMouseEnter={handleMouseEnter} />
      )}
      <div
        className={`header ${isMonitorPage && !visible ? 'header-hidden' : ''}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {/* Left: logo + set selector */}
        <div className="header-left">
          <h1 className="header-title">GRYPHONE</h1>
          {isMonitorPage && Object.keys(sets).length > 0 && (
            <select
              className="set-selector"
              value={currentSet}
              onChange={handleSetChange}
              title="Select set"
            >
              {Object.entries(sets).map(([id, set]) => (
                <option key={id} value={id}>{set.name}</option>
              ))}
            </select>
          )}
        </div>

        {/* Center: clock */}
        <div className="header-center">
          <span className="header-clock">{clock}</span>
        </div>

        {/* Right: hamburger menu */}
        <div className="header-right">
          <HamburgerMenu />
        </div>
      </div>
    </>
  )
}
HEADERJSX

echo "  [OK] Header.jsx восстановлен (версия до патча 81)"

# ============================================================================
# ШАГ 3: Восстановление styles.css (убираем position:fixed для всех страниц)
# ============================================================================
echo ""
echo "--- ШАГ 3: Восстановление styles.css ---"

# Проверяем наличие бэкапа до патча 82
if [ -f "$CSS_FILE.bak-82" ]; then
    echo "  [INFO] Найден бэкап $CSS_FILE.bak-82"
    cp "$CSS_FILE.bak-82" "$CSS_FILE"
    echo "  [OK] styles.css восстановлен из бэкапа .bak-82"
elif [ -f "$CSS_FILE.bak-81" ]; then
    echo "  [INFO] Найден бэкап $CSS_FILE.bak-81"
    cp "$CSS_FILE.bak-81" "$CSS_FILE"
    echo "  [OK] styles.css восстановлен из бэкапа .bak-81"
elif [ -f "$CSS_FILE.bak-80" ]; then
    echo "  [INFO] Найден бэкап $CSS_FILE.bak-80"
    cp "$CSS_FILE.bak-80" "$CSS_FILE"
    echo "  [OK] styles.css восстановлен из бэкапа .bak-80"
elif [ -f "$CSS_FILE.bak-79" ]; then
    echo "  [INFO] Найден бэкап $CSS_FILE.bak-79"
    cp "$CSS_FILE.bak-79" "$CSS_FILE"
    echo "  [OK] styles.css восстановлен из бэкапа .bak-79"
else
    echo "  [WARN] Бэкапы не найдены, применяем точечные исправления"

    # Точечное исправление: убираем position:fixed из .header
    python3 - "$CSS_FILE" << 'PYEOF'
import sys
from pathlib import Path

css_file = Path(sys.argv[1])
content = css_file.read_text(encoding="utf-8")

# Убираем все блоки PATCH-82, PATCH-83, PATCH-84
import re

# Удаляем блоки PATCH
content = re.sub(r'/\*\s*PATCH-82:.*?\*/\s*\n([\s\S]*?)(?=\n/\*|\Z)', '', content)
content = re.sub(r'/\*\s*PATCH-83:.*?\*/\s*\n([\s\S]*?)(?=\n/\*|\Z)', '', content)
content = re.sub(r'/\*\s*PATCH-84:.*?\*/\s*\n([\s\S]*?)(?=\n/\*|\Z)', '', content)

# Убираем position:fixed из .header
content = re.sub(r'\.header\s*\{[^}]*position:\s*fixed[^}]*\}', '', content, flags=re.DOTALL)

css_file.write_text(content, encoding="utf-8")
print("  [OK] Применены точечные исправления")
PYEOF
fi

# ============================================================================
# ШАГ 4: Проверка синтаксиса
# ============================================================================
echo ""
echo "--- ШАГ 4: Проверка синтаксиса ---"

# Проверяем Header.jsx
if node -e "require('fs').readFileSync('$HEADER_FILE', 'utf8')" 2>/dev/null; then
    echo "  [OK] Header.jsx синтаксически корректен"
else
    echo "  [WARN] Не удалось проверить Header.jsx (node не доступен)"
fi

# Проверяем styles.css
python3 -c "
content = open('$CSS_FILE', encoding='utf-8').read()
open_count = content.count('{')
close_count = content.count('}')
if open_count == close_count:
    print(f'  [OK] styles.css: скобки сбалансированы ({open_count}/{close_count})')
else:
    print(f'  [WARN] styles.css: скобки НЕ сбалансированы ({open_count}/{close_count})')
" 2>/dev/null || echo "  [WARN] Не удалось проверить styles.css"

echo ""
echo "============================================================================"
echo "Готово! Откат к состоянию до патча 81 завершён."
echo ""
echo "Что восстановлено:"
echo "  • Автоскрытие ТОЛЬКО на главной странице (/)"
echo "  • header-trigger ТОЛЬКО на главной"
echo "  • Шапка НЕ фиксированная (не position:fixed)"
echo "  • Логотип: GRYPHONE (не GRYPHONE-VISION)"
echo "  • Селектор наборов: слева в header-left"
echo ""
echo "Обязательно пересоберите фронтенд:"
echo "  cd $PROJECT_ROOT/frontend"
echo "  npm run build"
echo ""
echo "Резервные копии текущего состояния:"
echo "  • $HEADER_FILE.bak-99-before"
echo "  • $CSS_FILE.bak-99-before"
echo "============================================================================"