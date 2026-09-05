#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
118. update_scripts/118_griphone_vision_fullscreen.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  1. Заменяет надпись "GRYPHONE" на "GRYPHONE - VISION"
  2. Возвращает синий цвет (#2563eb) как раньше
  3. Добавляет полноэкранный режим по клику на логотип

ИЗМЕНЕНИЯ:
  • Header.jsx: текст логотипа, onClick, состояние isFullscreen
  • header.css: цвет заголовка #2563eb, hover-эффекты

ЗАПУСК: python update_scripts/118_griphone_vision_fullscreen.py
============================================================================
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("118: GRYPHONE - VISION с полноэкранным режимом")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # ========================================================================
    # ШАГ 1: Обновление Header.jsx
    # ========================================================================
    print("--- ШАГ 1: Обновление Header.jsx ---")
    header_jsx = project_root / "frontend/src/components/Header.jsx"
    backup_jsx = header_jsx.with_suffix(".jsx.bak-118")

    if not header_jsx.exists():
        print("  [ERROR] Header.jsx не найден")
        sys.exit(1)

    backup_jsx.write_text(header_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_jsx.name}")

    # Перезаписываем Header.jsx полностью
    new_header_jsx = """// ============================================================
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
"""

    header_jsx.write_text(new_header_jsx, encoding="utf-8")
    print("  [OK] Header.jsx обновлён")
    print("    • Логотип: GRYPHONE - VISION")
    print("    • onClick: переключение полноэкранного режима")
    print("    • Состояние isFullscreen добавлено")
    print()

    # ========================================================================
    # ШАГ 2: Обновление header.css (цвет и эффекты)
    # ========================================================================
    print("--- ШАГ 2: Обновление header.css ---")
    header_css = project_root / "frontend/src/styles/header.css"
    backup_css = header_css.with_suffix(".css.bak-118")

    if not header_css.exists():
        print("  [ERROR] header.css не найден")
        sys.exit(1)

    backup_css.write_text(header_css.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_css.name}")

    content = header_css.read_text(encoding="utf-8")

    # Ищем блок .header-title и заменяем его
    old_title = """.header-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #e0e3e8;
  margin: 0;
  white-space: nowrap;
  letter-spacing: 0.5px;
  /* Тень для читаемости на любом фоне */
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
}"""

    new_title = """.header-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #2563eb;
  margin: 0;
  white-space: nowrap;
  letter-spacing: 1px;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s ease;
  padding: 4px 8px;
  border-radius: 4px;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
}

.header-title:hover {
  background: rgba(37, 99, 235, 0.15);
  color: #3b82f6;
  transform: scale(1.02);
}

.header-title:active {
  transform: scale(0.98);
}

.header-title.fullscreen-active {
  color: #10b981;
  text-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
}

.header-title.fullscreen-active:hover {
  color: #059669;
  background: rgba(16, 185, 129, 0.15);
}"""

    if old_title in content:
        content = content.replace(old_title, new_title)
        header_css.write_text(content, encoding="utf-8")
        print("  [OK] header.css обновлён")
        print("    • Цвет: #2563eb (синий, как раньше)")
        print("    • cursor: pointer (указатель)")
        print("    • hover: синяя подсветка")
        print("    • fullscreen-active: зелёный цвет")
    else:
        print("  [WARN] Не удалось найти блок .header-title для замены")
        print("  Применю стили вручную...")
        content += "\n" + new_title
        header_css.write_text(content, encoding="utf-8")
        print("  [OK] Стили добавлены в конец файла")
    print()

    # ========================================================================
    # ИТОГ
    # ========================================================================
    print("=" * 76)
    print("Готово!")
    print()
    print("Что изменено:")
    print("  • Логотип: 'GRYPHONE' → 'GRYPHONE - VISION'")
    print("  • Цвет: #e0e3e8 (серый) → #2563eb (синий)")
    print("  • Клик по логотипу: вход/выход в полноэкранный режим")
    print("  • В полноэкранном режиме: зелёный цвет (#10b981)")
    print()
    print("Эффекты:")
    print("  • Наведение: синяя подсветка фона + увеличение")
    print("  • Клик: масштабирование")
    print("  • В полноэкранном: зелёный цвет + свечение")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print("Резервные копии:")
    print("  • Header.jsx.bak-118")
    print("  • header.css.bak-118")
    print("=" * 76)


if __name__ == "__main__":
    main()