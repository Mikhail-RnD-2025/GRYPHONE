#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
113. update_scripts/113_hamburger_menu_style.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Приводит стиль выпадающей панели меню (гамбургер) к единому стилю
  с шапкой: полупрозрачный градиент, размытие, тени для текста.

ИЗМЕНЕНИЯ:
  • Фон меню: непрозрачный (#1e293b) → полупрозрачный градиент
  • Добавлено размытие: backdrop-filter: blur(8px)
  • Границы: непрозрачные → полупрозрачные
  • Пункты меню: полупрозрачный фон при наведении
  • Тени для текста для читаемости

СТИЛЬ ЕДИНЫЙ С ШАПКОЙ:
  Шапка: градиент 0.5 → 0.4 → 0.2 + blur(8px)
  Меню:  градиент 0.85 → 0.75 → 0.65 + blur(8px)
  (меню чуть плотнее для читаемости пунктов)

ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
ЗАПУСК: python update_scripts/113_hamburger_menu_style.py
============================================================================
"""

import sys
import re
from pathlib import Path


def main():
    project_root = Path.cwd()
    hamburger_css = project_root / "frontend/src/styles/hamburger.css"
    backup_css = project_root / "frontend/src/styles/hamburger.css.bak-113"

    print("=" * 76)
    print("113: Стиль панели меню как у шапки")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # ========================================================================
    # ШАГ 1: Проверка существования файла
    # ========================================================================
    print("--- ШАГ 1: Проверка файла ---")
    if not hamburger_css.exists():
        print("  [ERROR] Файл hamburger.css не найден")
        sys.exit(1)
    print(f"  [OK] Найден файл: {hamburger_css}")
    print()

    # ========================================================================
    # ШАГ 2: Резервная копия
    # ========================================================================
    print("--- ШАГ 2: Резервная копия ---")
    backup_css.write_text(hamburger_css.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_css.name}")
    print()

    # ========================================================================
    # ШАГ 3: Анализ текущего состояния
    # ========================================================================
    print("--- ШАГ 3: Анализ текущего состояния ---")
    content = hamburger_css.read_text(encoding="utf-8")

    # Проверяем, применён ли уже новый стиль
    marker = "rgba(11, 13, 16, 0.85) 0%"
    if marker in content:
        print("  [OK] Стиль панели меню уже приведён к стилю шапки")
        print("  Повторное применение не требуется")
        print()
        print("=" * 76)
        print("Ничего не изменено. Файл уже в целевом состоянии.")
        print("=" * 76)
        return

    print("  Текущий фон выпадающего меню:")
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('background:') and 'dropdown' not in stripped:
            print(f"    {stripped}")
    print()

    # ========================================================================
    # ШАГ 4: Применение нового стиля
    # ========================================================================
    print("--- ШАГ 4: Применение стиля шапки к панели меню ---")

    new_content = """/* ============================================================
   Меню гамбургера — ЕДИНЫЙ СТИЛЬ с шапкой
   (полупрозрачный градиент + размытие)
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
  /* Тень для видимости на любом фоне */
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
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

/* Выпадающая панель — стиль как у шапки */
.hamburger-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 220px;
  /* Полупрозрачный градиент (чуть плотнее шапки для читаемости) */
  background: linear-gradient(
    to bottom,
    rgba(11, 13, 16, 0.85) 0%,
    rgba(11, 13, 16, 0.75) 70%,
    rgba(11, 13, 16, 0.65) 100%
  );
  backdrop-filter: blur(8px);
  border: 1px solid rgba(51, 65, 85, 0.3);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  padding: 8px;
  z-index: 2000;
  animation: dropdown-in 0.15s ease;
}

@keyframes dropdown-in {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Пункты меню */
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
  /* Тень для читаемости на полупрозрачном фоне */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

/* Наведение: полупрозрачный фон */
.hamburger-item:hover {
  background: rgba(51, 65, 85, 0.4);
}

/* Активный пункт: полупрозрачный синий */
.hamburger-item.active {
  background: rgba(37, 99, 235, 0.6);
  color: #fff;
}

/* Неактивный пункт */
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

/* Бейдж "скоро" */
.hamburger-item-badge {
  font-size: 0.7rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
}
"""

    hamburger_css.write_text(new_content, encoding="utf-8")
    print("  [OK] hamburger.css обновлён")
    print()
    print("  Применённые изменения:")
    print("    • Фон меню: градиент 0.85 → 0.75 → 0.65")
    print("    • Размытие: backdrop-filter: blur(8px)")
    print("    • Граница: rgba(51, 65, 85, 0.3)")
    print("    • Наведение: rgba(51, 65, 85, 0.4)")
    print("    • Активный пункт: rgba(37, 99, 235, 0.6)")
    print("    • Тени для текста и линий гамбургера")
    print()

    # ========================================================================
    # ШАГ 5: Проверка синтаксиса
    # ========================================================================
    print("--- ШАГ 5: Проверка синтаксиса ---")
    final_content = hamburger_css.read_text(encoding="utf-8")
    open_count = final_content.count('{')
    close_count = final_content.count('}')

    if open_count == close_count:
        print(f"  [OK] Скобки сбалансированы ({open_count}/{close_count})")
    else:
        print(f"  [FAIL] Скобки НЕ сбалансированы ({open_count}/{close_count})")
        print(f"  Восстановите из бэкапа: {backup_css.name}")
        sys.exit(1)
    print()

    # ========================================================================
    # ИТОГ
    # ========================================================================
    print("=" * 76)
    print("Готово! Панель меню теперь в едином стиле с шапкой.")
    print()
    print("Единый стиль:")
    print("  • Шапка: градиент 0.5 → 0.4 → 0.2 + blur(8px)")
    print("  • Меню:  градиент 0.85 → 0.75 → 0.65 + blur(8px)")
    print("  • Оба элемента: полупрозрачные, с размытием и тенями")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print(f"Резервная копия: {backup_css.name}")
    print("=" * 76)


if __name__ == "__main__":
    main()