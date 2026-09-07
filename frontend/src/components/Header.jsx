import { useState, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { getSets, switchSet } from '../api'
import HamburgerMenu from './HamburgerMenu'

export default function Header() {
  const [sets, setSets] = useState({})
  const [currentSet, setCurrentSet] = useState('')  // PATCH-178: пусто при старте
  const [clock, setClock] = useState('')
  const [visible, setVisible] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const hideTimerRef = useRef(null)
  const isHoveredRef = useRef(false)
  const location = useLocation()
  const isMonitorPage = location.pathname === '/'

  // PATCH-178: состояние кастомного dropdown
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [searchFilter, setSearchFilter] = useState('')
  const dropdownRef = useRef(null)
  const searchInputRef = useRef(null)

  useEffect(() => { loadSets() }, [])

  useEffect(() => {
    const id = setInterval(() => {
      const now = new Date()
      setClock(
        now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
      )
    }, 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false)
        setSearchFilter('')
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (dropdownOpen && searchInputRef.current) {
      setTimeout(() => searchInputRef.current?.focus(), 50)
    }
  }, [dropdownOpen])

  const loadSets = async () => {
    try {
      const data = await getSets()
      setSets(data.sets || {})
      // PATCH-182: последний выбор хранится ЛОКАЛЬНО в браузере
      const stored = localStorage.getItem('gryphone_current_set') || ''
      if (stored && data.sets && data.sets[stored]) {
        setCurrentSet(stored)
        switchSet(stored).catch(() => {})  // синхронизируем сервер
      } else {
        setCurrentSet('')
      }
    } catch (e) {
      console.error('Failed to load sets:', e)
    }
  }

  const handleSetChange = async (setId) => {
    setCurrentSet(setId)
    localStorage.setItem('gryphone_current_set', setId)  // PATCH-182
    setDropdownOpen(false)
    setSearchFilter('')
    try {
      await switchSet(setId)
      window.dispatchEvent(new CustomEvent('set-changed', { detail: { setId } }))
    } catch (e) {
      console.error('Failed to switch set:', e)
    }
  }

  const handleMouseEnter = () => {
    isHoveredRef.current = true
    setVisible(true)
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current)
      hideTimerRef.current = null
    }
  }

  const handleMouseLeave = () => {
    isHoveredRef.current = false
    hideTimerRef.current = setTimeout(() => {
      if (!isHoveredRef.current) setVisible(false)
    }, 800)
  }

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {})
      setIsFullscreen(true)
    } else {
      document.exitFullscreen().catch(() => {})
      setIsFullscreen(false)
    }
  }

  useEffect(() => {
    const handleFsChange = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', handleFsChange)
    return () => document.removeEventListener('fullscreenchange', handleFsChange)
  }, [])

  const setEntries = Object.entries(sets)
  const filteredSets = setEntries.filter(([id, s]) => {
    if (!searchFilter) return true
    const q = searchFilter.toLowerCase()
    return (
      id.toLowerCase().includes(q) ||
      (s.name || '').toLowerCase().includes(q)
    )
  })
  const currentSetName = currentSet && sets[currentSet]
    ? sets[currentSet].name
    : '— выберите набор —'

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
          {isMonitorPage && setEntries.length > 0 && (
            <div className="set-dropdown" ref={dropdownRef}>
              <button
                className={`set-selector ${!currentSet ? 'set-selector-empty' : ''}`}
                onClick={() => setDropdownOpen(o => !o)}
                type="button"
              >
                <span className="set-selector-label">{currentSetName}</span>
                <span className="set-selector-arrow">{dropdownOpen ? '▲' : '▼'}</span>
              </button>
              {dropdownOpen && (
                <div className="set-dropdown-menu">
                  <div className="set-dropdown-search">
                    <input
                      ref={searchInputRef}
                      type="text"
                      className="set-dropdown-input"
                      placeholder="🔍 Поиск набора..."
                      value={searchFilter}
                      onChange={(e) => setSearchFilter(e.target.value)}
                    />
                  </div>
                  <div className="set-dropdown-list">
                    {filteredSets.length === 0 ? (
                      <div className="set-dropdown-empty">Ничего не найдено</div>
                    ) : (
                      filteredSets.map(([id, s]) => (
                        <button
                          key={id}
                          type="button"
                          className={`set-dropdown-item ${id === currentSet ? 'active' : ''}`}
                          onClick={() => handleSetChange(id)}
                        >
                          <span className="set-dropdown-item-name">{s.name}</span>  {/* PATCH-179: только имя */}
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
          <HamburgerMenu />
        </div>
      </div>
    </>
  )
}
