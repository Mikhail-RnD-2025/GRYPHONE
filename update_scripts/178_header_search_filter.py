#!/usr/bin/env python3
"""
178. update_scripts/178_header_search_filter.py
----------------------------------------------------------------------------
АВТОПОИСК КОРНЯ: идёт вверх по дереву, пока не найдёт папку frontend/
  • можно запускать из любого места (update_scripts/, frontend/, корень)

ЗАПУСК:
  python update_scripts/178_header_search_filter.py          # из корня
  cd update_scripts && python ./178_header_search_filter.py  # из update_scripts
"""

import sys
from pathlib import Path


NEW_HEADER_JSX = r'''import { useState, useEffect, useRef } from 'react'
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
      setCurrentSet('')  // PATCH-178
    } catch (e) {
      console.error('Failed to load sets:', e)
    }
  }

  const handleSetChange = async (setId) => {
    setCurrentSet(setId)
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
                          <span className="set-dropdown-item-name">{s.name}</span>
                          <span className="set-dropdown-item-meta">
                            {s.max_columns || 0}×{s.max_rows || 0} · {s.aspect_ratio || '16:9'}
                          </span>
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
'''

MONITOR_PATCH = '''      {!setData && (
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          background: '#1e293b', borderRadius: '8px',
          border: '1px dashed #334155',
          margin: '40px auto', maxWidth: '500px',
        }}>
          <div style={{ fontSize: '1.25rem', marginBottom: '12px' }}>
            📹 Наборы не созданы
          </div>
          <div style={{ color: '#94a3b8', marginBottom: '20px' }}>
            Для начала работы создайте набор камер и добавьте в него камеры.
          </div>
          <Link to="/settings" className="btn btn-primary">
            Перейти в настройки
          </Link>
        </div>
      )}

      {setData && !hasSets && (
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          background: '#1e293b', borderRadius: '8px',
          border: '1px dashed #334155',
          margin: '40px auto', maxWidth: '500px',
        }}>
          <div style={{ fontSize: '1.25rem', marginBottom: '12px' }}>
            📹 Выберите набор
          </div>
          <div style={{ color: '#94a3b8', marginBottom: '20px' }}>
            Наведите курсор на верх страницы и выберите набор в шапке.
          </div>
        </div>
      )}'''

CSS_PATCH = """
/* PATCH-178: кастомный dropdown с поиском */
.set-dropdown {
  position: relative;
  min-width: 220px;
  max-width: 360px;
}
.set-selector {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 6px;
  color: #e0e3e8;
  font-size: 0.85rem;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.set-selector:hover {
  border-color: #3b82f6;
  background: rgba(30, 41, 59, 0.8);
}
.set-selector-empty { color: #94a3b8; font-style: italic; }
.set-selector-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.set-selector-arrow { font-size: 0.7rem; color: #64748b; }

.set-dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 260px;
  max-width: 400px;
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(51, 65, 85, 0.7);
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(8px);
  z-index: 100;
  overflow: hidden;
}
.set-dropdown-search {
  padding: 8px;
  border-bottom: 1px solid rgba(51, 65, 85, 0.5);
}
.set-dropdown-input {
  width: 100%;
  padding: 6px 10px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 4px;
  color: #e0e3e8;
  font-size: 0.85rem;
  outline: none;
}
.set-dropdown-input:focus { border-color: #3b82f6; }
.set-dropdown-list { max-height: 320px; overflow-y: auto; }
.set-dropdown-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 8px 12px;
  background: transparent;
  border: none;
  color: #e0e3e8;
  font-size: 0.85rem;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease;
}
.set-dropdown-item:hover { background: rgba(37, 99, 235, 0.2); }
.set-dropdown-item.active {
  background: rgba(37, 99, 235, 0.3);
  border-left: 3px solid #3b82f6;
  padding-left: 9px;
}
.set-dropdown-item-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.set-dropdown-item-meta { font-size: 0.7rem; color: #64748b; white-space: nowrap; }
.set-dropdown-empty {
  padding: 14px 12px;
  color: #64748b;
  font-size: 0.8rem;
  text-align: center;
  font-style: italic;
}
"""


def find_project_root():
    """Идёт вверх по дереву, пока не найдёт папку frontend/"""
    p = Path.cwd()
    while True:
        if (p / "frontend").is_dir() and (p / "update_scripts").is_dir():
            return p
        parent = p.parent
        if parent == p:
            print("[FAIL] Не найден корень проекта (папки frontend/ и update_scripts/)")
            print("       Запустите из корня: cd /c/GRYPHONE_PROJ/v26")
            sys.exit(1)
        p = parent


def main():
    project_root = find_project_root()
    print(f"  [OK] Корень проекта: {project_root}")
    print()

    header = project_root / "frontend" / "src" / "components" / "Header.jsx"
    monitor = project_root / "frontend" / "src" / "pages" / "MonitorPage.jsx"
    css_file = project_root / "frontend" / "src" / "styles" / "header.css"

    print("=" * 76)
    print("178: пустой селект при старте + кастомный dropdown с поиском")
    print("=" * 76)
    print()

    # --- Header.jsx ---
    print("--- Header.jsx ---")
    b = header.with_suffix(".jsx.bak-178")
    b.write_text(header.read_text(encoding="utf-8"), encoding="utf-8")
    if NEW_HEADER_JSX.count('{') != NEW_HEADER_JSX.count('}'):
        print("  [FAIL] скобки — откат"); sys.exit(1)
    header.write_text(NEW_HEADER_JSX, encoding="utf-8")
    print("  [OK] Header перезаписан")

    # --- MonitorPage.jsx ---
    print()
    print("--- MonitorPage.jsx ---")
    b = monitor.with_suffix(".jsx.bak-178")
    b.write_text(monitor.read_text(encoding="utf-8"), encoding="utf-8")
    c = monitor.read_text(encoding="utf-8")

    if "PATCH-178" in c:
        print("  [OK] Уже применён")
    else:
        old = """      {!hasSets && (
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          background: '#1e293b', borderRadius: '8px',
          border: '1px dashed #334155',
          margin: '40px auto', maxWidth: '500px',
        }}>
          <div style={{ fontSize: '1.25rem', marginBottom: '12px' }}>
            📹 Наборы не созданы
          </div>
          <div style={{ color: '#94a3b8', marginBottom: '20px' }}>
            Для начала работы создайте набор камер и добавьте в него камеры.
          </div>
          <Link to="/settings" className="btn btn-primary">
            Перейти в настройки
          </Link>
        </div>
      )}"""
        if old in c:
            c = c.replace(old, MONITOR_PATCH, 1)
            if c.count('{') == c.count('}'):
                monitor.write_text(c, encoding="utf-8")
                print("  [OK] блок «Наборы не созданы» → «Выберите набор»")
            else:
                print("  [FAIL] скобки — откат")
                monitor.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
                sys.exit(1)
        else:
            print("  [FAIL] якорь не найден — откат")
            monitor.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

    # --- header.css ---
    print()
    print("--- header.css ---")
    css = css_file.read_text(encoding="utf-8") if css_file.exists() else ""
    if "PATCH-178" not in css:
        css += CSS_PATCH
        css_file.write_text(css, encoding="utf-8")
        print("  [OK] стили dropdown")
    else:
        print("  [OK] стили уже есть")

    print()
    print("=" * 76)
    print("✅ Готово!")
    print()
    print("Поведение:")
    print("  • При загрузке: селект пустой (— выберите набор —)")
    print("  • В мониторинге: «📹 Выберите набор» пока ничего не выбрано")
    print("  • Клик по селектору → dropdown с полем поиска")
    print("  • Фильтр по имени и ID набора")
    print("  • В каждой опции: имя + размер + формат")
    print()
    print(f"  cd {project_root}/frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит (из корня проекта):")
    print()
    print(f"cd {project_root}")
    print("git add -A")
    print('git commit -m "ui: empty set selector at start + searchable dropdown (PATCH-178)" \\')
    print('  -m "Header: currentSet empty on load, user picks set explicitly" \\')
    print('  -m "Header: custom dropdown with search filter over name/id" \\')
    print('  -m "MonitorPage: new state «Выберите набор» when set not picked"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()