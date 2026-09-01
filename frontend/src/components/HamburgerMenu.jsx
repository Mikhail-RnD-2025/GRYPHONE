// ============================================================
//  GRYPHONE — hamburger menu (mobile-style)
//  ------------------------------------------------------------
//  Three-stripe button that opens a dropdown with navigation.
//  Menu items (in order):
//    1. Status     (dashboard moved here)
//    2. Analytics  (placeholder)
//    3. Reports    (placeholder)
//    4. Cameras
//    5. Sets
//    6. Settings
//    7. Help
// ============================================================
import { useState, useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'

const MENU_ITEMS = [
  { path: '/', label: 'Главная', icon: '🏠', enabled: true },

  { path: '/status',     label: 'Состояние',  icon: '📊', enabled: true  },
  { path: '/analytics',  label: 'Аналитика',  icon: '📈', enabled: false },
  { path: '/reports',    label: 'Отчёты',     icon: '📋', enabled: false },
  { path: '/cameras',    label: 'Камеры',     icon: '📹', enabled: true  },
  { path: '/sets',       label: 'Мониторинг',     icon: '📦', enabled: true  },
  { path: '/settings',   label: 'Настройки',  icon: '⚙️', enabled: true  },
  { path: '/help',       label: 'Справка',    icon: '❓', enabled: true  },
]

export default function HamburgerMenu() {
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)
  const location = useLocation()

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
