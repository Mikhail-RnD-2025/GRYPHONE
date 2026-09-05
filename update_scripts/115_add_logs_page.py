#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
115. update_scripts/115_add_logs_page.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Добавляет страницу "Логи" в приложение:
  1. Создаёт компонент LogsPage.jsx
  2. Добавляет пункт "Логи" в меню гамбургера
  3. Добавляет роут /logs в App.jsx

ЗАПУСК: python update_scripts/115_add_logs_page.py
============================================================================
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("115: Добавление страницы Логи")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # ========================================================================
    # ШАГ 1: Создание компонента LogsPage.jsx
    # ========================================================================
    print("--- ШАГ 1: Создание LogsPage.jsx ---")
    pages_dir = project_root / "frontend/src/pages"
    logs_page = pages_dir / "LogsPage.jsx"

    if logs_page.exists():
        print(f"  [OK] Файл уже существует: {logs_page.name}")
        backup = logs_page.with_suffix(".jsx.bak-115")
        backup.write_text(logs_page.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  [BAK] {backup.name}")
    else:
        print(f"  [INFO] Создаём новый файл: {logs_page.name}")

    logs_page_content = """// ============================================================
// GRYPHONE — страница логов
// ------------------------------------------------------------
// Отображает системные логи приложения в реальном времени.
// ============================================================

import { useState, useEffect, useRef } from 'react'
import Header from '../components/Header'

export default function LogsPage() {
  const [logs, setLogs] = useState([])
  const [filter, setFilter] = useState('all')
  const logsEndRef = useRef(null)

  // Загрузка логов с сервера
  useEffect(() => {
    loadLogs()
    const interval = setInterval(loadLogs, 5000) // Обновление каждые 5 сек
    return () => clearInterval(interval)
  }, [])

  const loadLogs = async () => {
    try {
      const response = await fetch('/api/logs')
      if (response.ok) {
        const data = await response.json()
        setLogs(data.logs || [])
      } else {
        // Если API недоступен, показываем заглушку
        setLogs([
          { timestamp: new Date().toISOString(), level: 'INFO', message: 'Система логов будет доступна после настройки сервера' },
          { timestamp: new Date().toISOString(), level: 'DEBUG', message: 'Заглушка логов для демонстрации интерфейса' },
        ])
      }
    } catch (e) {
      console.error('Ошибка загрузки логов:', e)
    }
  }

  // Автоскролл к последним логам
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const getLevelColor = (level) => {
    switch (level) {
      case 'ERROR': return '#dc2626'
      case 'WARNING': return '#d97706'
      case 'INFO': return '#059669'
      case 'DEBUG': return '#94a3b8'
      default: return '#e0e3e8'
    }
  }

  const filteredLogs = filter === 'all' 
    ? logs 
    : logs.filter(log => log.level.toLowerCase() === filter)

  return (
    <div className="page">
      <Header />
      <div className="section-header">
        <div className="section-header-left">
          <span className="section-icon">📜</span>
          <h1 className="section-title">Логи системы</h1>
        </div>
      </div>

      {/* Фильтр по уровню */}
      <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {['all', 'error', 'warning', 'info', 'debug'].map(level => (
          <button
            key={level}
            className={`btn ${filter === level ? 'btn-primary' : ''}`}
            onClick={() => setFilter(level)}
            style={{ padding: '6px 12px', fontSize: '0.8125rem' }}
          >
            {level === 'all' ? 'Все' : level.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Контейнер логов */}
      <div style={{
        background: '#0b0d10',
        border: '1px solid #1e293b',
        borderRadius: '8px',
        padding: '16px',
        overflowY: 'auto',
        flex: 1,
        minHeight: 0,
        fontFamily: 'Courier New, monospace',
        fontSize: '0.8125rem',
        lineHeight: 1.6,
      }}>
        {filteredLogs.length === 0 ? (
          <div style={{ color: '#64748b', textAlign: 'center', padding: '40px' }}>
            Нет логов для отображения
          </div>
        ) : (
          filteredLogs.map((log, index) => (
            <div key={index} style={{
              padding: '4px 0',
              borderBottom: '1px solid rgba(30, 41, 59, 0.5)',
              display: 'flex',
              gap: '12px',
            }}>
              <span style={{ color: '#64748b', flexShrink: 0 }}>
                {new Date(log.timestamp).toLocaleTimeString('ru-RU')}
              </span>
              <span style={{ 
                color: getLevelColor(log.level), 
                fontWeight: 600, 
                minWidth: '70px',
                flexShrink: 0,
              }}>
                [{log.level}]
              </span>
              <span style={{ color: '#e0e3e8' }}>{log.message}</span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  )
}
"""

    logs_page.write_text(logs_page_content, encoding="utf-8")
    print(f"  [OK] Создан компонент: {logs_page.name}")
    print()

    # ========================================================================
    # ШАГ 2: Добавление пункта "Логи" в меню гамбургера
    # ========================================================================
    print("--- ШАГ 2: Добавление пункта в меню ---")
    hamburger_menu = project_root / "frontend/src/components/HamburgerMenu.jsx"
    backup_menu = hamburger_menu.with_suffix(".jsx.bak-115")

    if hamburger_menu.exists():
        backup_menu.write_text(hamburger_menu.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  [BAK] {backup_menu.name}")

        menu_content = hamburger_menu.read_text(encoding="utf-8")

        # Проверяем, есть ли уже пункт логов
        if "'/logs'" in menu_content or '"/logs"' in menu_content:
            print("  [OK] Пункт 'Логи' уже существует в меню")
        else:
            # Ищем массив MENU_ITEMS и добавляем пункт логов
            # Вставляем после пункта 'Наборы' и перед 'Настройки'
            old_line = "  { path: '/sets', label: 'Наборы', icon: '📦', enabled: true },"
            new_line = """  { path: '/sets', label: 'Наборы', icon: '📦', enabled: true },
  { path: '/logs', label: 'Логи', icon: '📜', enabled: true },"""

            if old_line in menu_content:
                menu_content = menu_content.replace(old_line, new_line)
                hamburger_menu.write_text(menu_content, encoding="utf-8")
                print("  [OK] Добавлен пункт '📜 Логи' в меню")
            else:
                print("  [WARN] Не удалось найти место для вставки пункта")
                print("  Попробуйте добавить вручную в массив MENU_ITEMS:")
                print("    { path: '/logs', label: 'Логи', icon: '📜', enabled: true },")
    else:
        print("  [ERROR] Файл HamburgerMenu.jsx не найден")
    print()

    # ========================================================================
    # ШАГ 3: Добавление роута в App.jsx
    # ========================================================================
    print("--- ШАГ 3: Добавление роута в App.jsx ---")
    app_jsx = project_root / "frontend/src/App.jsx"
    backup_app = app_jsx.with_suffix(".jsx.bak-115")

    if app_jsx.exists():
        backup_app.write_text(app_jsx.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  [BAK] {backup_app.name}")

        app_content = app_jsx.read_text(encoding="utf-8")

        # Проверяем, есть ли уже роут логов
        if '/logs' in app_content:
            print("  [OK] Роут '/logs' уже существует")
        else:
            # Добавляем импорт LogsPage
            if "import LogsPage from './pages/LogsPage'" not in app_content:
                old_import = "import HelpPage from './pages/HelpPage'"
                new_import = """import HelpPage from './pages/HelpPage'
import LogsPage from './pages/LogsPage'"""
                app_content = app_content.replace(old_import, new_import)
                print("  [OK] Добавлен импорт LogsPage")

            # Добавляем роут
            old_route = """<Route path="/help" element={<HelpPage />} />"""
            new_route = """<Route path="/help" element={<HelpPage />} />
        <Route path="/logs" element={<LogsPage />} />"""

            if old_route in app_content:
                app_content = app_content.replace(old_route, new_route)
                app_jsx.write_text(app_content, encoding="utf-8")
                print("  [OK] Добавлен роут '/logs'")
            else:
                print("  [WARN] Не удалось найти место для роута")
                print("  Попробуйте добавить вручную:")
                print("    <Route path=\"/logs\" element={<LogsPage />} />")
    else:
        print("  [ERROR] Файл App.jsx не найден")
    print()

    # ========================================================================
    # ИТОГ
    # ========================================================================
    print("=" * 76)
    print("Готово! Страница Логи добавлена.")
    print()
    print("Что создано/изменено:")
    print("  • frontend/src/pages/LogsPage.jsx — компонент страницы логов")
    print("  • frontend/src/components/HamburgerMenu.jsx — добавлен пункт '📜 Логи'")
    print("  • frontend/src/App.jsx — добавлен роут '/logs'")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print("Резервные копии:")
    print("  • LogsPage.jsx.bak-115 (если файл существовал)")
    print("  • HamburgerMenu.jsx.bak-115")
    print("  • App.jsx.bak-115")
    print("=" * 76)


if __name__ == "__main__":
    main()