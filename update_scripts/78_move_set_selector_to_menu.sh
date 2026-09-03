#!/bin/sh
# ============================================================================
# 78. update_scripts/78_move_set_selector_to_menu.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Перемещает выбор наборов из Header в HamburgerMenu. Теперь выпадающий
#   список наборов появляется в меню гамбургера, а не в шапке страницы.
#
# ИЗМЕНЕНИЯ:
#   1. HamburgerMenu.jsx — добавлена секция выбора наборов в начало меню
#   2. Header.jsx — удалён <select> из header-left
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./78_move_set_selector_to_menu.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "78: Перемещение выбора наборов в меню гамбургера"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

MENU_FILE="frontend/src/components/HamburgerMenu.jsx"
HEADER_FILE="frontend/src/components/Header.jsx"

if [ ! -f "$MENU_FILE" ]; then
    echo "ОШИБКА: не найден $MENU_FILE" >&2; exit 1
fi
if [ ! -f "$HEADER_FILE" ]; then
    echo "ОШИБКА: не найден $HEADER_FILE" >&2; exit 1
fi

# ============================================================================
# ШАГ 1: Резервные копии
# ============================================================================
echo ""
echo "--- ШАГ 1: Резервные копии ---"
cp "$MENU_FILE" "$MENU_FILE.bak-78"
cp "$HEADER_FILE" "$HEADER_FILE.bak-78"
echo "  [BAK] $MENU_FILE.bak-78"
echo "  [BAK] $HEADER_FILE.bak-78"

# ============================================================================
# ШАГ 2: Обновление HamburgerMenu.jsx
# ============================================================================
echo ""
echo "--- ШАГ 2: Обновление HamburgerMenu.jsx ---"

cat > "$MENU_FILE" << 'MENUJSX'
// ============================================================
// GRYPHONE — hamburger menu (mobile-style)
// ------------------------------------------------------------
// Three-stripe button that opens a dropdown with navigation.
// PATCH-78: добавлен выбор наборов в начало меню.
// ============================================================

import { useState, useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getSets, switchSet } from '../api'

const MENU_ITEMS = [
  { path: '/', label: 'Мониторинг', icon: '📹', enabled: true },
  { path: '/status', label: 'Состояние', icon: '📊', enabled: true },
  { path: '/analytics', label: 'Аналитика', icon: '📈', enabled: false },
  { path: '/reports', label: 'Отчёты', icon: '📋', enabled: false },
  { path: '/cameras', label: 'Камеры', icon: '📹', enabled: true },
  { path: '/sets', label: 'Наборы', icon: '📦', enabled: true },
  { path: '/settings', label: 'Настройки', icon: '⚙️', enabled: true },
  { path: '/help', label: 'Справка', icon: '❓', enabled: true },
]

export default function HamburgerMenu() {
  const [open, setOpen] = useState(false)
  const [sets, setSets] = useState({})
  const [currentSet, setCurrentSet] = useState('')
  const menuRef = useRef(null)
  const location = useLocation()

  // Загружаем наборы при открытии меню
  useEffect(() => {
    if (open) {
      loadSets()
    }
  }, [open])

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

  // Close menu on outside click
  useEffect(() => {
    if (!open) return
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  // Close menu on route change
  useEffect(() => {
    setOpen(false)
  }, [location.pathname])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handleEsc = (e) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [open])

  return (
    <div className="hamburger-menu" ref={menuRef}>
      <button
        className={`hamburger-btn ${open ? 'active' : ''}`}
        onClick={() => setOpen(!open)}
        aria-label="Menu"
        aria-expanded={open}
      >
        <span className="hamburger-line" />
        <span className="hamburger-line" />
        <span className="hamburger-line" />
      </button>

      {open && (
        <div className="hamburger-dropdown">
          {/* PATCH-78: Секция выбора наборов */}
          {Object.keys(sets).length > 0 && (
            <div className="hamburger-sets-section">
              <div className="hamburger-sets-label">📦 Набор:</div>
              <select
                className="hamburger-sets-select"
                value={currentSet}
                onChange={handleSetChange}
              >
                {Object.entries(sets).map(([id, set]) => (
                  <option key={id} value={id}>
                    {set.name}
                  </option>
                ))}
              </select>
              <div className="hamburger-divider" />
            </div>
          )}

          {/* Основные пункты меню */}
          {MENU_ITEMS.map((item) => {
            const isActive = location.pathname === item.path
            const isDisabled = !item.enabled

            if (isDisabled) {
              return (
                <div
                  key={item.path}
                  className="hamburger-item disabled"
                  title="Скоро"
                >
                  <span className="hamburger-item-icon">{item.icon}</span>
                  <span className="hamburger-item-label">{item.label}</span>
                  <span className="hamburger-item-badge">скоро</span>
                </div>
              )
            }

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`hamburger-item ${isActive ? 'active' : ''}`}
              >
                <span className="hamburger-item-icon">{item.icon}</span>
                <span className="hamburger-item-label">{item.label}</span>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
MENUJSX

echo "  [FIXED] HamburgerMenu.jsx обновлён"

# ============================================================================
# ШАГ 3: Обновление Header.jsx (удаление select)
# ============================================================================
echo ""
echo "--- ШАГ 3: Обновление Header.jsx ---"

cat > "$HEADER_FILE" << 'HEADERJSX'
import { useState, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import HamburgerMenu from './HamburgerMenu'

export default function Header() {
  const [clock, setClock] = useState('')
  const [visible, setVisible] = useState(true)
  const hideTimerRef = useRef(null)
  const isHoveredRef = useRef(false)
  const location = useLocation()
  const isMonitorPage = location.pathname === '/'

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
        {/* Left: logo only (set selector moved to HamburgerMenu) */}
        <div className="header-left">
          <h1 className="header-title">GRYPHONE</h1>
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

echo "  [FIXED] Header.jsx обновлён (select удалён)"

# ============================================================================
# ШАГ 4: Добавление стилей для секции наборов
# ============================================================================
echo ""
echo "--- ШАГ 4: Обновление стилей ---"

CSS_FILE="frontend/src/index.css"
if [ -f "$CSS_FILE" ]; then
    # Проверяем, есть ли уже стили для hamburger-sets
    if grep -q "hamburger-sets-section" "$CSS_FILE"; then
        echo "  [OK] Стили для секции наборов уже есть"
    else
        # Добавляем стили перед последним комментарием или в конец
        cat >> "$CSS_FILE" << 'CSSEOF'

/* PATCH-78: Стили для секции выбора наборов в меню */
.hamburger-sets-section {
  padding: 12px 16px;
  border-bottom: 1px solid #334155;
}

.hamburger-sets-label {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.hamburger-sets-select {
  width: 100%;
  padding: 8px 12px;
  background: #1e293b;
  color: #e2e8f0;
  border: 1px solid #475569;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: border-color 0.2s;
}

.hamburger-sets-select:hover {
  border-color: #64748b;
}

.hamburger-sets-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.hamburger-divider {
  height: 1px;
  background: #334155;
  margin: 8px 0;
}
CSSEOF
        echo "  [FIXED] Добавлены стили для секции наборов"
    fi
else
    echo "  [WARN] $CSS_FILE не найден, стили не добавлены"
fi

echo ""
echo "============================================================================"
echo "Готово. Резервные копии: *.bak-78"
echo ""
echo "Обязательно пересоберите фронтенд:"
echo "  cd $PROJECT_ROOT/frontend"
echo "  npm run build"
echo ""
echo "Теперь выбор наборов находится в меню гамбургера (три полоски справа)."
echo "============================================================================"