#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
109_unify_header_style.py

Делает шапку стилистически одинаковой на всех страницах по образцу главной:
- Единый градиентный фон с прозрачностью
- Единый backdrop-filter: blur
- Единая высота и отступы
- Автоскрытие остаётся только на главной (функциональная разница),
  но визуально шапка выглядит одинаково везде.

ЗАПУСК: python update_scripts/109_unify_header_style.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    header_css = project_root / "frontend/src/styles/header.css"
    backup = project_root / "frontend/src/styles/header.css.bak-109"

    print("=" * 76)
    print("109: Единый стиль шапки на всех страницах")
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

    # ШАГ 2: Создание единого стиля шапки
    print("--- ШАГ 2: Применение единого стиля ---")

    new_content = """/* ============================================================
   Шапка приложения — ЕДИНЫЙ СТИЛЬ на всех страницах
   (по образцу главной страницы мониторинга)
   ============================================================ */

/* Базовый блок: одинаковые стили для ВСЕХ страниц */
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
  border-bottom: 1px solid rgba(51, 65, 85, 0.3);
  transition: transform 0.3s ease, opacity 0.3s ease;
  transform: translateY(0);
  opacity: 1;
  z-index: 1000;
}

/* На мониторинге: шапка — фиксированный оверлей */
.page.monitor-page .header,
.monitor-page .header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
}

/* На остальных страницах: шапка статичная, но с ТЕМ ЖЕ стилем */
.page:not(.monitor-page) .header {
  position: relative;
}

/* Скрытое состояние (только на мониторинге) */
.header.header-hidden {
  transform: translateY(-100%);
  opacity: 0;
  pointer-events: none;
}

/* Триггер-зона для появления шапки (только на мониторинге) */
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

    header_css.write_text(new_content, encoding="utf-8")
    print("  [OK] header.css обновлён с единым стилем")
    print()
    print("  Что применено ко ВСЕМ страницам:")
    print("    • Градиентный фон: rgba(11,13,16,0.95) → rgba(11,13,16,0.4)")
    print("    • backdrop-filter: blur(8px)")
    print("    • border-bottom: 1px solid rgba(51,65,85,0.3)")
    print("    • height: 56px, padding: 8px 16px")
    print("    • z-index: 1000")
    print()
    print("  Функциональные отличия (не визуальные):")
    print("    • Главная: position: fixed + автоскрытие через триггер-зону")
    print("    • Остальные: position: relative (всегда видна)")
    print()

    # ШАГ 3: Также обновим логотип в Header.jsx (если нужно)
    print("--- ШАГ 3: Проверка Header.jsx ---")
    header_jsx = project_root / "frontend/src/components/Header.jsx"
    if header_jsx.exists():
        jsx_content = header_jsx.read_text(encoding="utf-8")
        if "GRYPHONE-VISION" not in jsx_content and "GRYPHONE" in jsx_content:
            print("  [INFO] Логотип в Header.jsx: GRYPHONE")
        elif "GRYPHONE-VISION" in jsx_content:
            print("  [INFO] Логотип в Header.jsx: GRYPHONE-VISION")
    print()

    print("=" * 76)
    print("Готово! Шапка теперь стилистически одинакова на всех страницах.")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print(f"Резервная копия: {backup.name}")
    print("=" * 76)


if __name__ == "__main__":
    main()