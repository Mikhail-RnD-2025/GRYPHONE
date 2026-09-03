#!/bin/sh
# ============================================================================
# 80. update_scripts/80_fullscreen_logo.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   1. Меняет логотип с "GRYPHONE" на "GRYPHONE-VISION"
#   2. Добавляет переключение полноэкранного режима по клику на логотип
#   3. Добавляет визуальные эффекты (курсор, подсветка при наведении)
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./80_fullscreen_logo.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "80: Логотип GRYPHONE-VISION с полноэкранным режимом"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

HEADER_FILE="frontend/src/components/Header.jsx"
CSS_FILE="frontend/src/index.css"

if [ ! -f "$HEADER_FILE" ]; then
    echo "ОШИБКА: не найден $HEADER_FILE" >&2; exit 1
fi

# ============================================================================
# ШАГ 1: Резервная копия
# ============================================================================
echo ""
echo "--- ШАГ 1: Резервная копия ---"
cp "$HEADER_FILE" "$HEADER_FILE.bak-80"
echo "  [BAK] $HEADER_FILE.bak-80"

# ============================================================================
# ШАГ 2: Обновление Header.jsx
# ============================================================================
echo ""
echo "--- ШАГ 2: Обновление Header.jsx ---"

cat > "$HEADER_FILE" << 'HEADERJSX'
import { useState, useEffect, useRef, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import { getSets, switchSet } from '../api'
import HamburgerMenu from './HamburgerMenu'

export default function Header() {
  const [sets, setSets] = useState({})
  const [currentSet, setCurrentSet] = useState('')
  const [clock, setClock] = useState('')
  const [visible, setVisible] = useState(true)
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

  // PATCH-80: Отслеживаем изменения полноэкранного режима
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  // PATCH-80: Переключение полноэкранного режима
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
        {/* Left: logo with fullscreen toggle */}
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

        {/* Center: clock */}
        <div className="header-center">
          <span className="header-clock">{clock}</span>
        </div>

        {/* Right: set selector + hamburger menu */}
        <div className="header-right">
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
HEADERJSX

echo "  [FIXED] Header.jsx обновлён"
echo "  Добавлено: логотип GRYPHONE-VISION + полноэкранный режим по клику"

# ============================================================================
# ШАГ 3: Добавление стилей
# ============================================================================
echo ""
echo "--- ШАГ 3: Обновление стилей ---"

if [ -f "$CSS_FILE" ]; then
    if grep -q "header-title.*cursor" "$CSS_FILE" && grep -q "fullscreen-active" "$CSS_FILE"; then
        echo "  [OK] Стили для логотипа уже есть"
    else
        cat >> "$CSS_FILE" << 'CSSEOF'

/* PATCH-80: Логотип GRYPHONE-VISION с полноэкранным режимом */
.header-title {
  cursor: pointer;
  user-select: none;
  transition: all 0.2s ease;
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
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

.header-title.fullscreen-active:hover {
  color: #059669;
  background: rgba(16, 185, 129, 0.1);
}
CSSEOF
        echo "  [FIXED] Добавлены стили для логотипа"
    fi
else
    echo "  [WARN] $CSS_FILE не найден, стили не добавлены"
fi

echo ""
echo "============================================================================"
echo "Готово. Резервная копия: $HEADER_FILE.bak-80"
echo ""
echo "Обязательно пересоберите фронтенд:"
echo "  cd $PROJECT_ROOT/frontend"