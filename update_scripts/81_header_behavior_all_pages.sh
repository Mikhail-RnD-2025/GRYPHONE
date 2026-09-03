#!/bin/sh
# ============================================================================
# 81. update_scripts/81_header_behavior_all_pages.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Делает поведение Header одинаковым на всех страницах:
#   • Header скрывается и показывается по наведению (как на главной)
#   • header-trigger работает на всех страницах
#   • Селектор наборов остаётся только на главной странице (/)
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./81_header_behavior_all_pages.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "81: Единое поведение шапки на всех страницах"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

HEADER_FILE="frontend/src/components/Header.jsx"

if [ ! -f "$HEADER_FILE" ]; then
    echo "ОШИБКА: не найден $HEADER_FILE" >&2; exit 1
fi

# ============================================================================
# ШАГ 1: Резервная копия
# ============================================================================
echo ""
echo "--- ШАГ 1: Резервная копия ---"
cp "$HEADER_FILE" "$HEADER_FILE.bak-81"
echo "  [BAK] $HEADER_FILE.bak-81"

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

  // PATCH-81: Auto-hide logic на ВСЕХ страницах (а не только на главной)
  useEffect(() => {
    setVisible(false)
  }, [location.pathname])

  const cancelHide = () => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current)
      hideTimerRef.current = null
    }
  }

  // PATCH-81: Schedule hide на ВСЕХ страницах
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

  // PATCH-81: handleMouseLeave на ВСЕХ страницах
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
      {/* PATCH-81: header-trigger на ВСЕХ страницах */}
      <div className="header-trigger" onMouseEnter={handleMouseEnter} />

      <div
        className={`header ${!visible ? 'header-hidden' : ''}`}
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

        {/* Right: set selector (ONLY on monitor page) + hamburger menu */}
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
echo "  Изменения:"
echo "    • Автоскрытие Header — на всех страницах"
echo "    • header-trigger — на всех страницах"
echo "    • Селектор наборов — только на главной (/)"

echo ""
echo "============================================================================"
echo "Готово. Резервная копия: $HEADER_FILE.bak-81"
echo ""
echo "Обязательно пересоберите фронтенд:"
echo "  cd $PROJECT_ROOT/frontend"
echo "  npm run build"
echo ""
echo "Теперь поведение шапки одинаковое на всех страницах:"
echo "  • Наведите мышь на верх страницы → шапка появится"
echo "  • Уберите мышь → через 2 секунды шапка скроется"
echo "  • Селектор наборов виден только на главной (/)"
echo "============================================================================"