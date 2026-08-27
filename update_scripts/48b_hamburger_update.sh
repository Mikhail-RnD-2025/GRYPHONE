#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 48b: UPDATE EXISTING FILES
#  ------------------------------------------------------------
#  Updates:
#    1. Header.jsx        — replace nav buttons with hamburger
#    2. App.jsx           — add new routes
#    3. SettingsPage.jsx  — remove Dashboard tab
#    4. styles.css        — hamburger menu styles
#
#  RUN:   bash update_scripts/48b_hamburger_update.sh
#  THEN:  bash build_frontend.sh && python main.py
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

# ============================================================
# Python detection
# ============================================================
_detect_python() {
    local cmd
    for cmd in python python3 py; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" --version >/dev/null 2>&1; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    if command -v py >/dev/null 2>&1; then
        if py -3 --version >/dev/null 2>&1; then
            echo "py -3"
            return 0
        fi
    fi
    return 1
}

PYTHON_CMD="$(_detect_python || true)"
if [ -z "$PYTHON_CMD" ]; then
    echo "❌ ERROR: no Python interpreter found."
    exit 1
fi
read -ra PYCMD <<< "$PYTHON_CMD"
echo "✅ Python: ${PYCMD[*]}"

# ============================================================
# PART 1: Rewrite Header.jsx (hamburger only on right)
# ============================================================
echo ""
echo "🔧 Rewriting Header.jsx..."

cat > "$PROJECT_DIR/frontend/src/components/Header.jsx" << 'HEADER_END'
// ============================================================
//  GRYPHONE — application header (v48)
//  ------------------------------------------------------------
//  Left:   logo
//  Center: clock
//  Right:  hamburger menu (all navigation moved there)
// ============================================================
import { useState, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { getSets, switchSet } from '../api'
import HamburgerMenu from './HamburgerMenu'

export default function Header() {
  const [sets, setSets] = useState({})
  const [currentSet, setCurrentSet] = useState('')
  const [clock, setClock] = useState('')
  const [visible, setVisible] = useState(false)
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
HEADER_END
echo "  ✔ frontend/src/components/Header.jsx"

# ============================================================
# PART 2: Rewrite App.jsx (add new routes)
# ============================================================
echo ""
echo "🔧 Rewriting App.jsx..."

cat > "$PROJECT_DIR/frontend/src/App.jsx" << 'APPEOF'
// ============================================================
//  GRYPHONE — main application component (v48)
// ============================================================
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MonitorPage from './pages/MonitorPage'
import StatusPage from './pages/StatusPage'
import AnalyticsPage from './pages/AnalyticsPage'
import ReportsPage from './pages/ReportsPage'
import CamerasPage from './pages/CamerasPage'
import SetsPage from './pages/SetsPage'
import SettingsPage from './pages/SettingsPage'
import HelpPage from './pages/HelpPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MonitorPage />} />
        <Route path="/status" element={<StatusPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/cameras" element={<CamerasPage />} />
        <Route path="/sets" element={<SetsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/help" element={<HelpPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
APPEOF
echo "  ✔ frontend/src/App.jsx"

# ============================================================
# PART 3: Rewrite SettingsPage.jsx (remove Dashboard tab)
# ============================================================
echo ""
echo "🔧 Rewriting SettingsPage.jsx (Dashboard removed)..."

cat > "$PROJECT_DIR/frontend/src/pages/SettingsPage.jsx" << 'SETTINGS_END'
// ============================================================
//  GRYPHONE — settings page (v48)
//  Dashboard moved to /status, only config remains here
// ============================================================
import { useState, useEffect } from 'react'
import Header from '../components/Header'
import Help from '../components/Help'
import Toasts from '../components/Toasts'
import { getConfig } from '../api'

export default function SettingsPage() {
  const [configData, setConfigData] = useState(null)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const config = await getConfig()
      setConfigData(config)
    } catch (e) {
      console.error('Failed to load config:', e)
    }
  }

  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">⚙️ Настройки</h1>
      <div className="tab-content">
        <h2>Конфигурация системы</h2>
        {configData ? (
          <pre style={{
            background: '#0b0d10', padding: '16px', borderRadius: '8px',
            overflow: 'auto', fontSize: '0.875rem', maxHeight: '600px',
          }}>
            {JSON.stringify(configData, null, 2)}
          </pre>
        ) : (
          <p>Загрузка...</p>
        )}
      </div>
      <Toasts />
    </div>
  )
}
SETTINGS_END
echo "  ✔ frontend/src/pages/SettingsPage.jsx"

# ============================================================
# PART 4: Add hamburger styles to styles.css
# ============================================================
echo ""
echo "🔧 Adding hamburger styles to styles.css..."

STYLES_FILE="$PROJECT_DIR/frontend/src/styles.css"

if grep -q '.hamburger-menu' "$STYLES_FILE" 2>/dev/null; then
    echo "  ℹ️  Hamburger styles already present — skipping"
else
    cat >> "$STYLES_FILE" << 'STYLES_END'

/* ============================================================
   Hamburger menu (v48)
   ============================================================ */

.hamburger-menu {
  position: relative;
}

.hamburger-btn {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  width: 32px;
  height: 24px;
  padding: 4px 0;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.hamburger-btn:hover {
  transform: scale(1.1);
}

.hamburger-line {
  display: block;
  width: 100%;
  height: 2px;
  background: #e0e3e8;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.hamburger-btn.active .hamburger-line:nth-child(1) {
  transform: translateY(11px) rotate(45deg);
}
.hamburger-btn.active .hamburger-line:nth-child(2) {
  opacity: 0;
}
.hamburger-btn.active .hamburger-line:nth-child(3) {
  transform: translateY(-11px) rotate(-45deg);
}

.hamburger-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 220px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  padding: 8px;
  z-index: 2000;
  animation: dropdown-in 0.15s ease;
}

@keyframes dropdown-in {
  from { opacity: 0; transform: translateY(-8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.hamburger-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  color: #e0e3e8;
  text-decoration: none;
  border-radius: 6px;
  transition: background 0.15s ease;
  font-size: 0.9rem;
  cursor: pointer;
}

.hamburger-item:hover {
  background: #334155;
}

.hamburger-item.active {
  background: #2563eb;
  color: #fff;
}

.hamburger-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hamburger-item-icon {
  font-size: 1.1rem;
  width: 24px;
  text-align: center;
}

.hamburger-item-label {
  flex: 1;
}

.hamburger-item-badge {
  font-size: 0.7rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
}

/* Placeholder card for future pages */
.placeholder-card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 60px 40px;
  text-align: center;
  margin: 40px auto;
  max-width: 500px;
}

.placeholder-icon {
  font-size: 4rem;
  margin-bottom: 16px;
}

.placeholder-card h2 {
  margin-bottom: 12px;
  color: #e0e3e8;
}

.placeholder-card p {
  color: #94a3b8;
  margin-bottom: 24px;
  line-height: 1.5;
}
STYLES_END
    echo "  ✔ Hamburger styles added to styles.css"
fi

# ============================================================
# Final check
# ============================================================
echo ""
echo "🔍 Final check..."

for f in \
  frontend/src/components/Header.jsx \
  frontend/src/components/HamburgerMenu.jsx \
  frontend/src/App.jsx \
  frontend/src/pages/SettingsPage.jsx \
  frontend/src/pages/StatusPage.jsx \
  frontend/src/pages/AnalyticsPage.jsx \
  frontend/src/pages/ReportsPage.jsx \
  frontend/src/pages/CamerasPage.jsx \
  frontend/src/pages/SetsPage.jsx \
  frontend/src/styles.css; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ERROR: file $f is empty or missing!" >&2
    exit 1
  fi
  echo "  ✔ $f"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Part 48b complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Menu items (in order):"
echo "  1. 📊 Состояние    → /status     (dashboard)"
echo "  2. 📈 Аналитика    → /analytics  (placeholder)"
echo "  3. 📋 Отчёты       → /reports    (placeholder)"
echo "  4. 📹 Камеры       → /cameras"
echo "  5. 📦 Наборы       → /sets"
echo "  6. ⚙️ Настройки    → /settings"
echo "  7. ❓ Справка      → /help"
echo ""
echo "🚀 Next steps:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Open: http://localhost:5000 (Ctrl+Shift+R)"