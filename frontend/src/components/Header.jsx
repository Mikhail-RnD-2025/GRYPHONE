// ============================================================
// GRYPHONE-VISION — application header (v118)
// ------------------------------------------------------------
// Шапка-оверлей с автоскрытием на ВСЕХ страницах.
// Логотип "GRYPHONE - VISION" (синий) + полноэкранный режим по клику.
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react'
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

  // Отслеживаем изменения полноэкранного режима
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  // Переключение полноэкранного режима по клику на логотип
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

  // Автоскрытие на ВСЕХ страницах
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
            GRYPHONE - VISION
          </h1>
        </div>

        <div className="header-center">
          <span className="header-clock">{clock}</span>
        </div>

        <div className="header-right">
          {isMonitorPage && Object.keys(sets).length > 0 && (
            <select
              className="set-selector"
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
