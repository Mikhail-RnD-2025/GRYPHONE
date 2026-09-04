#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
108_fix_header_height.py

Исправляет высоту шапки, чтобы она была одинаковой на всех страницах.

ЗАПУСК: python update_scripts/108_fix_header_height.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    header_css = project_root / "frontend/src/styles/header.css"
    backup = project_root / "frontend/src/styles/header.css.bak-108"

    print("=" * 76)
    print("108: Исправление высоты шапки (единая на всех страницах)")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # ШАГ 1: Резервная копия
    print("--- ШАГ 1: Резервная копия ---")
    if header_css.exists():
        backup.write_text(header_css.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  [BAK] {backup.name}")
    else:
        print("  [ERROR] Файл header.css не найден")
        sys.exit(1)
    print()

    # ШАГ 2: Исправление стилей
    print("--- ШАГ 2: Исправление стилей ---")

    new_content = """/* ============================================================
   Шапка приложения (ИСПРАВЛЕНО: единая высота на всех страницах)
   ============================================================ */

.header {
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
  transition: transform 0.3s ease, opacity 0.3s ease;
  transform: translateY(0);
  opacity: 1;
}

/* На мониторинге: шапка — оверлей (fixed) */
.page.monitor-page .header,
.monitor-page .header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
}

/* На не-мониторинге: шапка статичная (relative), НО с той же высотой */
.page:not(.monitor-page) .header {
  position: relative;
  background: rgba(11, 13, 16, 0.98);
}

/* Скрытое состояние (только на мониторинге) */
.header.header-hidden {
  transform: translateY(-100%);
  opacity: 0;
  pointer-events: none;
}

/* Триггер-зона (только на мониторинге) */
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

/* Левая часть: логотип */
.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  min-width: 0;
}

.header-title {
  font-size: 1.25rem;
  color: #2563eb;
  margin: 0;
  white-space: nowrap;
}

/* Центральная часть: время */
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
  font-family: monospace;
}

/* Правая часть: наборы → навигация → справка */
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
  background: #334155;
  color: #e0e3e8;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.875rem;
  transition: background 0.2s ease;
  white-space: nowrap;
}

.header-btn:hover {
  background: #475569;
}
"""

    header_css.write_text(new_content, encoding="utf-8")
    print("  [OK] header.css обновлён")
    print("  Изменения:")
    print("    • Убрана позиция из базового .header")
    print("    • height: 56px теперь в базовом блоке (для всех страниц)")
    print("    • padding: 8px 16px — одинаковый на всех страницах")
    print("    • position добавляется только в .page.monitor-page и .page:not(.monitor-page)")
    print()

    print("=" * 76)
    print("Готово!")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print(f"Резервная копия: {backup.name}")
    print("=" * 76)


if __name__ == "__main__":
    main()