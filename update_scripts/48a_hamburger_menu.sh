#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 48a: HAMBURGER MENU + NEW PAGES
#  ------------------------------------------------------------
#  Creates:
#    1. HamburgerMenu.jsx — dropdown menu component
#    2. StatusPage.jsx    — dashboard moved here
#    3. AnalyticsPage.jsx — placeholder
#    4. ReportsPage.jsx   — placeholder
#
#  RUN:   bash update_scripts/48a_hamburger_menu.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/main.py" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
else
    PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
fi

echo "📁 Project root: $PROJECT_DIR"
cd "$PROJECT_DIR"
echo "📂 Working directory: $(pwd)"

mkdir -p "$PROJECT_DIR/frontend/src/components"
mkdir -p "$PROJECT_DIR/frontend/src/pages"

# ============================================================
# PART 1: HamburgerMenu.jsx
# ============================================================
echo ""
echo "🔧 Creating HamburgerMenu.jsx..."

cat > "$PROJECT_DIR/frontend/src/components/HamburgerMenu.jsx" << 'JSXEOF'
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
  { path: '/status',     label: 'Состояние',  icon: '📊', enabled: true  },
  { path: '/analytics',  label: 'Аналитика',  icon: '📈', enabled: false },
  { path: '/reports',    label: 'Отчёты',     icon: '📋', enabled: false },
  { path: '/cameras',    label: 'Камеры',     icon: '📹', enabled: true  },
  { path: '/sets',       label: 'Наборы',     icon: '📦', enabled: true  },
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
JSXEOF
echo "  ✔ frontend/src/components/HamburgerMenu.jsx"

# ============================================================
# PART 2: StatusPage.jsx (dashboard moved here)
# ============================================================
echo ""
echo "🔧 Creating StatusPage.jsx..."

cat > "$PROJECT_DIR/frontend/src/pages/StatusPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — status page (dashboard moved from settings)
// ============================================================
import Header from '../components/Header'
import Dashboard from '../components/Dashboard'
import Toasts from '../components/Toasts'

export default function StatusPage() {
  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">📊 Состояние системы</h1>
      <div className="tab-content">
        <Dashboard />
      </div>
      <Toasts />
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/StatusPage.jsx"

# ============================================================
# PART 3: AnalyticsPage.jsx (placeholder)
# ============================================================
echo ""
echo "🔧 Creating AnalyticsPage.jsx..."

cat > "$PROJECT_DIR/frontend/src/pages/AnalyticsPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — analytics page (placeholder for future)
// ============================================================
import { Link } from 'react-router-dom'
import Header from '../components/Header'

export default function AnalyticsPage() {
  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">📈 Аналитика</h1>
      <div className="placeholder-card">
        <div className="placeholder-icon">📈</div>
        <h2>Раздел в разработке</h2>
        <p>Здесь будет аналитика по камерам, событиям и нагрузке системы.</p>
        <Link to="/" className="btn btn-primary">← На главную</Link>
      </div>
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/AnalyticsPage.jsx"

# ============================================================
# PART 4: ReportsPage.jsx (placeholder)
# ============================================================
echo ""
echo "🔧 Creating ReportsPage.jsx..."

cat > "$PROJECT_DIR/frontend/src/pages/ReportsPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — reports page (placeholder for future)
// ============================================================
import { Link } from 'react-router-dom'
import Header from '../components/Header'

export default function ReportsPage() {
  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">📋 Отчёты</h1>
      <div className="placeholder-card">
        <div className="placeholder-icon">📋</div>
        <h2>Раздел в разработке</h2>
        <p>Здесь будут отчёты по доступности камер, событиям и архивам.</p>
        <Link to="/" className="btn btn-primary">← На главную</Link>
      </div>
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/ReportsPage.jsx"

# ============================================================
# PART 5: CamerasPage.jsx (wrapper for CamerasEditor)
# ============================================================
echo ""
echo "🔧 Creating CamerasPage.jsx..."

cat > "$PROJECT_DIR/frontend/src/pages/CamerasPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — cameras editor page
// ============================================================
import Header from '../components/Header'
import CamerasEditor from '../components/CamerasEditor'
import Toasts from '../components/Toasts'

export default function CamerasPage() {
  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">📹 Редактор камер</h1>
      <div className="tab-content">
        <CamerasEditor />
      </div>
      <Toasts />
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/CamerasPage.jsx"

# ============================================================
# PART 6: SetsPage.jsx (sets management)
# ============================================================
echo ""
echo "🔧 Creating SetsPage.jsx..."

cat > "$PROJECT_DIR/frontend/src/pages/SetsPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — sets management page
// ============================================================
import { useState, useEffect } from 'react'
import Header from '../components/Header'
import Toasts from '../components/Toasts'
import { getSets, saveSets } from '../api'

export default function SetsPage() {
  const [setsData, setSetsData] = useState(null)
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const sets = await getSets()
      setSetsData(sets)
    } catch (e) {
      console.error('Failed to load sets:', e)
    }
  }

  const handleSaveSets = async () => {
    try {
      await saveSets(setsData)
      if (window.addToast) {
        window.addToast('✅ Sets saved', 'success')
      }
    } catch (e) {
      console.error('Failed to save sets:', e)
      if (window.addToast) {
        window.addToast('❌ Failed to save sets', 'error')
      }
    }
  }

  const handleExcelImport = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    if (!file.name.endsWith('.xls') && !file.name.endsWith('.xlsx')) {
      if (window.addToast) {
        window.addToast('❌ Invalid format. Use .xlsx or .xls', 'error')
      }
      return
    }

    setImporting(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/cameras/import-excel', {
        method: 'POST',
        body: formData,
      })
      const result = await response.json()

      if (result.success) {
        if (window.addToast) {
          window.addToast(`✅ ${result.message}. Press F5`, 'success')
        }
        await loadData()
      } else {
        if (window.addToast) {
          window.addToast(`❌ ${result.message}`, 'error')
        }
      }
    } catch (e) {
      if (window.addToast) {
        window.addToast(`❌ Import error: ${e.message}`, 'error')
      }
    } finally {
      setImporting(false)
      event.target.value = ''
    }
  }

  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">📦 Управление наборами</h1>

      <div className="tab-content">
        <div style={{
          marginBottom: '20px', padding: '16px',
          background: '#1e293b', borderRadius: '8px',
          border: '1px solid #334155',
        }}>
          <h3 style={{ marginBottom: '12px' }}>📥 Import from Excel</h3>
          <p style={{ color: '#94a3b8', marginBottom: '12px' }}>
            Required columns: <strong>ID</strong>, <strong>main_url</strong>.
            Optional: name, sub_url, enabled, comment, audio, location.
          </p>
          <label className="btn btn-primary" style={{ cursor: 'pointer' }}>
            {importing ? '⏳ Loading...' : '📥 Choose Excel file'}
            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={handleExcelImport}
              disabled={importing}
              style={{ display: 'none' }}
            />
          </label>
        </div>

        {setsData ? (
          <div>
            <p>Active set: <strong>{setsData.default_set || 'not selected'}</strong></p>
            <p>Total sets: <strong>{Object.keys(setsData.sets || {}).length}</strong></p>
            <div style={{ marginTop: '16px' }}>
              <button className="btn btn-primary" onClick={handleSaveSets}>
                💾 Save sets
              </button>
            </div>
          </div>
        ) : (
          <p>Loading...</p>
        )}
      </div>

      <Toasts />
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/SetsPage.jsx"

# ============================================================
# Final check
# ============================================================
echo ""
echo "🔍 Final check..."

for f in \
  frontend/src/components/HamburgerMenu.jsx \
  frontend/src/pages/StatusPage.jsx \
  frontend/src/pages/AnalyticsPage.jsx \
  frontend/src/pages/ReportsPage.jsx \
  frontend/src/pages/CamerasPage.jsx \
  frontend/src/pages/SetsPage.jsx; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ERROR: file $f is empty or missing!" >&2
    exit 1
  fi
  echo "  ✔ $f"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Part 48a complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Created:"
echo "  • HamburgerMenu.jsx"
echo "  • StatusPage.jsx (dashboard moved here)"
echo "  • AnalyticsPage.jsx (placeholder)"
echo "  • ReportsPage.jsx (placeholder)"
echo "  • CamerasPage.jsx"
echo "  • SetsPage.jsx"
echo ""
echo "Next: run 48b_hamburger_update.sh"