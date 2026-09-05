#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
119. update_scripts/119_blue_fullscreen_logo.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Изменяет цвет логотипа в полноэкранном режиме с зелёного на синий.
  Убирает зелёные цвета (#10b981, #059669) и заменяет на синие.

ИЗМЕНЕНИЯ:
  • .header-title.fullscreen-active: #10b981 (зелёный) → #2563eb (синий)
  • .header-title.fullscreen-active:hover: #059669 (тёмно-зелёный) → #3b82f6 (светло-синий)

ЦВЕТОВАЯ СХЕМА ПОСЛЕ ПАТЧА:
  Обычный режим:        #2563eb (ярко-синий)
  Наведение:            #3b82f6 (светло-синий)
  Полноэкранный режим:  #2563eb (ярко-синий) + усиленное свечение
  Полноэкранный + нав.: #3b82f6 (светло-синий)

ЗАПУСК: python update_scripts/119_blue_fullscreen_logo.py
============================================================================
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("119: Синий логотип в полноэкранном режиме")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # ========================================================================
    # ШАГ 1: Обновление header.css
    # ========================================================================
    print("--- ШАГ 1: Обновление header.css ---")
    header_css = project_root / "frontend/src/styles/header.css"
    backup_css = header_css.with_suffix(".css.bak-119")

    if not header_css.exists():
        print("  [ERROR] header.css не найден")
        sys.exit(1)

    backup_css.write_text(header_css.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_css.name}")

    content = header_css.read_text(encoding="utf-8")
    changes_made = []

    # 1. Заменяем зелёный цвет на синий в полноэкранном режиме
    old_fullscreen = """.header-title.fullscreen-active {
  color: #10b981;
  text-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
}"""

    new_fullscreen = """.header-title.fullscreen-active {
  color: #2563eb;
  text-shadow: 0 0 15px rgba(37, 99, 235, 0.6);
}"""

    if old_fullscreen in content:
        content = content.replace(old_fullscreen, new_fullscreen)
        changes_made.append("fullscreen-active: #10b981 (зелёный) → #2563eb (синий)")
    else:
        print("  [WARN] Не найден блок .header-title.fullscreen-active")

    # 2. Заменяем тёмно-зелёный на светло-синий в полноэкранном + наведении
    old_fullscreen_hover = """.header-title.fullscreen-active:hover {
  color: #059669;
  background: rgba(16, 185, 129, 0.15);
}"""

    new_fullscreen_hover = """.header-title.fullscreen-active:hover {
  color: #3b82f6;
  background: rgba(37, 99, 235, 0.15);
}"""

    if old_fullscreen_hover in content:
        content = content.replace(old_fullscreen_hover, new_fullscreen_hover)
        changes_made.append("fullscreen-active:hover: #059669 (тёмно-зелёный) → #3b82f6 (светло-синий)")
    else:
        print("  [WARN] Не найден блок .header-title.fullscreen-active:hover")

    # Сохраняем
    if changes_made:
        header_css.write_text(content, encoding="utf-8")
        print("  [OK] header.css обновлён")
        print()
        print("  Применённые изменения:")
        for change in changes_made:
            print(f"    • {change}")
    else:
        print("  [WARN] Изменения не применены")
    print()

    # ========================================================================
    # ШАГ 2: Проверка синтаксиса
    # ========================================================================
    print("--- ШАГ 2: Проверка синтаксиса ---")
    final_content = header_css.read_text(encoding="utf-8")
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
    print("Готово! Логотип теперь синий в полноэкранном режиме.")
    print()
    print("Цветовая схема:")
    print("  • Обычный режим:        #2563eb (ярко-синий)")
    print("  • Наведение:            #3b82f6 (светло-синий)")
    print("  • Полноэкранный режим:  #2563eb (ярко-синий) + свечение")
    print("  • Полноэкранный + нав.: #3b82f6 (светло-синий)")
    print()
    print("Эффект свечения усилен:")
    print("  • Было: 0 0 10px rgba(16, 185, 129, 0.4) — слабое зелёное")
    print("  • Стало: 0 0 15px rgba(37, 99, 235, 0.6) — сильное синее")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print(f"Резервная копия: {backup_css.name}")
    print("=" * 76)


if __name__ == "__main__":
    main()