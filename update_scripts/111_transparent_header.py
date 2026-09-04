#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
111_transparent_header.py

Делает шапку почти прозрачной:
- Фон едва заметен (opacity ~0.05-0.1)
- Убрано размытие (backdrop-filter)
- Элементы (логотип, часы, меню) остаются чётко видимыми

ЗАПУСК: python update_scripts/111_transparent_header.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("111: Почти прозрачная шапка")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # ШАГ 1: Обновление header.css
    print("--- ШАГ 1: Обновление header.css ---")
    header_css = project_root / "frontend/src/styles/header.css"
    backup_css = project_root / "frontend/src/styles/header.css.bak-111"

    if header_css.exists():
        backup_css.write_text(header_css.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  [BAK] {backup_css.name}")
    else:
        print("  [ERROR] header.css не найден")
        sys.exit(1)

    new_header_css = """/* ============================================================
   Шапка приложения — ПОЧТИ ПРОЗРАЧНАЯ
   (фон едва заметен, элементы чётко видимы)
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
  /* Почти прозрачный фон */
  background: rgba(11, 13, 16, 0.08);
  /* Без размытия — прозрачность максимальная */
  /* Тонкая нижняя граница для визуального разделения */
  border-bottom: 1px solid rgba(51, 65, 85, 0.2);
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
  /* Тень для читаемости на любом фоне */
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
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
  /* Тень для читаемости */
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
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
  background: rgba(51, 65, 85, 0.4);
  color: #e0e3e8;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.875rem;
  transition: background 0.2s ease, transform 0.1s ease;
  white-space: nowrap;
}

.header-btn:hover {
  background: rgba(71, 85, 105, 0.6);
  transform: scale(1.05);
}

.header-btn:active {
  transform: scale(0.95);
}
"""

    header_css.write_text(new_header_css, encoding="utf-8")
    print("  [OK] header.css обновлён")
    print("  Изменения:")
    print("    • Фон: rgba(11, 13, 16, 0.08) — почти прозрачный")
    print("    • Убран градиент и backdrop-filter")
    print("    • Добавлены тени для текста (читаемость на любом фоне)")
    print("    • Тонкая нижняя граница: rgba(51, 65, 85, 0.2)")
    print()

    # ШАГ 2: Обновление стилей селектора (если он есть)
    print("--- ШАГ 2: Обновление forms.css ---")
    forms_css = project_root / "frontend/src/styles/forms.css"

    if forms_css.exists():
        forms_content = forms_css.read_text(encoding="utf-8")

        # Обновляем селектор для прозрачной шапки
        new_forms_css = """/* ============================================================
   Селекторы и формы (для прозрачной шапки)
   ============================================================ */

.set-selector {
  background: rgba(30, 41, 59, 0.6);
  color: #e0e3e8;
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.875rem;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s ease, background 0.2s ease;
  /* Тень для читаемости */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.set-selector:hover {
  border-color: #2563eb;
  background: rgba(30, 41, 59, 0.8);
}

.set-selector:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}
"""

        forms_css.write_text(new_forms_css, encoding="utf-8")
        print("  [OK] forms.css обновлён")
        print("  Изменения:")
        print("    • Селектор стал полупрозрачным")
        print("    • Добавлена тень для читаемости")
    else:
        print("  [WARN] forms.css не найден, пропускаю")
    print()

    print("=" * 76)
    print("Готово! Шапка теперь почти прозрачная:")
    print("  • Фон едва заметен (opacity 0.08)")
    print("  • Элементы чётко видны благодаря теням")
    print("  • Контент просвечивает сквозь шапку")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print(f"Резервная копия: {backup_css.name}")
    print("=" * 76)


if __name__ == "__main__":
    main()