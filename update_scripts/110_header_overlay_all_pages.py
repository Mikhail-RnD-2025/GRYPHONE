#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
110_header_overlay_all_pages.py

Делает шапку фиксированной с автоскрытием на ВСЕХ страницах:
- Шапка скрывается при бездействии (2 сек)
- Появляется при наведении мыши на верх экрана
- Наползает на контент (оверлей)
- Поведение одинаковое на всех страницах

ЗАПУСК: python update_scripts/110_header_overlay_all_pages.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("110: Шапка-оверлей с автоскрытием на всех страницах")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # =========================================================================
    # ШАГ 1: Обновление Header.jsx
    # =========================================================================
    print("--- ШАГ 1: Обновление Header.jsx ---")
    header_jsx = project_root / "frontend/src/components/Header.jsx"
    backup_jsx = project_root / "frontend/src/components/Header.jsx.bak-110"

    if header_jsx.exists():
        backup_jsx.write_text(header_jsx.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  [BAK] {backup_jsx.name}")
    else:
        print("  [ERROR] Header.jsx не найден")
        sys.exit(1)

    new_header_jsx = """// ============================================================
// GRYPHONE-VISION — application header (v110)
// ------------------------------------------------------------
// Шапка-оверлей с автоскрытием на ВСЕХ страницах.
// Поведение одинаковое везде:
//   • Скрывается через 2 сек бездействия
//   • Появляется при наведении на верх экрана
//   • Наползает на контент (не резервирует место)
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

  // Автоскрытие на ВСЕХ страницах (не только на главной)
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
      {/* Триггер-зона на ВСЕХ страницах */}
      <div className="header-trigger" onMouseEnter={handleMouseEnter} />

      <div
        className={`header ${!visible ? 'header-hidden' : ''}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {/* Left: logo + set selector */}
        <div className="header-left">
          <h1 className="header-title">GRYPHONE</h1>
          {/* Селектор наборов только на главной */}
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
"""

    header_jsx.write_text(new_header_jsx, encoding="utf-8")
    print("  [OK] Header.jsx обновлён")
    print("  Изменения:")
    print("    • Триггер-зона на ВСЕХ страницах (не только на главной)")
    print("    • Автоскрытие на ВСЕХ страницах")
    print("    • Класс header-hidden применяется без проверки isMonitorPage")
    print()

    # =========================================================================
    # ШАГ 2: Обновление header.css
    # =========================================================================
    print("--- ШАГ 2: Обновление header.css ---")
    header_css = project_root / "frontend/src/styles/header.css"
    backup_css = project_root / "frontend/src/styles/header.css.bak-110"

    if header_css.exists():
        backup_css.write_text(header_css.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  [BAK] {backup_css.name}")

    new_header_css = """/* ============================================================
   Шапка приложения — ЕДИНЫЙ ОВЕРЛЕЙ на всех страницах
   (автоскрытие + наползание на контент)
   ============================================================ */

/* Базовый блок: фиксированная шапка на ВСЕХ страницах */
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  height: 56px;
  background: linear-gradient(
    to bottom,
    rgba(11, 13, 16, 0.95) 0%,
    rgba(11, 13, 16, 0.85) 70%,
    rgba(11, 13, 16, 0.4) 100%
  );
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(51, 65, 85, 0.3);
  transition: transform 0.3s ease, opacity 0.3s ease;
  transform: translateY(0);
  opacity: 1;
}

/* Скрытое состояние */
.header.header-hidden {
  transform: translateY(-100%);
  opacity: 0;
  pointer-events: none;
}

/* Триггер-зона для появления шапки */
.header-trigger {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 20px;
  z-index: 999;
  background: transparent;
  pointer-events: auto;
}

/* Левая часть: логотип + селектор наборов */
.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.header-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #e0e3e8;
  margin: 0;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

/* Центральная часть: часы */
.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  pointer-events: none;
}

.header-clock {
  font-size: 1rem;
  font-weight: 500;
  color: #e0e3e8;
  font-family: 'Courier New', monospace;
  letter-spacing: 1px;
}

/* Правая часть: меню гамбургера */
.header-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  min-width: 0;
}

.header-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 10px;
  background: rgba(51, 65, 85, 0.6);
  color: #e0e3e8;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.875rem;
  transition: background 0.2s ease, transform 0.1s ease;
  white-space: nowrap;
  backdrop-filter: blur(4px);
}

.header-btn:hover {
  background: rgba(71, 85, 105, 0.8);
  transform: scale(1.05);
}

.header-btn:active {
  transform: scale(0.95);
}
"""

    header_css.write_text(new_header_css, encoding="utf-8")
    print("  [OK] header.css обновлён")
    print("  Изменения:")
    print("    • position: fixed на ВСЕХ страницах (убраны условия)")
    print("    • Шапка всегда фиксированная и наползает на контент")
    print()

    # =========================================================================
    # ШАГ 3: Обновление layout.css (убрать отступы под шапку)
    # =========================================================================
    print("--- ШАГ 3: Обновление layout.css ---")
    layout_css = project_root / "frontend/src/styles/layout.css"
    backup_layout = project_root / "frontend/src/styles/layout.css.bak-110"

    if layout_css.exists():
        backup_layout.write_text(layout_css.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  [BAK] {backup_layout.name}")

        layout_content = layout_css.read_text(encoding="utf-8")

        # Убираем отступы под шапку
        layout_content = layout_content.replace(
            ".page:not(.monitor-page) {\n  padding-top: 12px;\n}",
            ".page:not(.monitor-page) {\n  padding-top: 0;\n}"
        )

        # Добавляем правило для всех страниц
        if "padding-top: 0" not in layout_content:
            layout_content += """
/* Все страницы: контент начинается с верха (шапка наползает) */
.page {
  padding-top: 0;
}
"""

        layout_css.write_text(layout_content, encoding="utf-8")
        print("  [OK] layout.css обновлён")
        print("  Изменения:")
        print("    • Убраны отступы под шапку на всех страницах")
        print("    • Контент начинается с верха экрана")
    else:
        print("  [WARN] layout.css не найден, пропускаю")
    print()

    print("=" * 76)
    print("Готово! Шапка теперь ведёт себя одинаково на всех страницах:")
    print("  • Скрывается через 2 сек бездействия")
    print("  • Появляется при наведении на верх экрана")
    print("  • Наползает на контент (не резервирует место)")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print("Резервные копии:")
    print("  • Header.jsx.bak-110")
    print("  • header.css.bak-110")
    print("  • layout.css.bak-110")
    print("=" * 76)


if __name__ == "__main__":
    main()