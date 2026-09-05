#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
117. update_scripts/117_move_selector_to_menu.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Перемещает селектор наборов из левой части шапки (рядом с логотипом)
  в правую часть (рядом с кнопкой гамбургера).

ИЗМЕНЕНИЯ:
  • Header.jsx: <select> перемещён из header-left в header-right
  • forms.css: добавлен класс .set-selector-right (если нужно)

РЕЗУЛЬТАТ:
  [GRYPHONE]          [12:34:56]          [🏢 210 ▼] ☰
                                          ↑ селектор рядом с меню

ЗАПУСК: python update_scripts/117_move_selector_to_menu.py
============================================================================
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("117: Перемещение селектора наборов к кнопке меню")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # ========================================================================
    # ШАГ 1: Обновление Header.jsx
    # ========================================================================
    print("--- ШАГ 1: Обновление Header.jsx ---")
    header_jsx = project_root / "frontend/src/components/Header.jsx"
    backup_jsx = header_jsx.with_suffix(".jsx.bak-117")

    if not header_jsx.exists():
        print("  [ERROR] Header.jsx не найден")
        sys.exit(1)

    backup_jsx.write_text(header_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_jsx.name}")

    content = header_jsx.read_text(encoding="utf-8")

    # Проверяем, есть ли уже селектор в header-right
    if 'className="set-selector-right"' in content or (
            'header-right' in content and 'set-selector' in content and content.index('header-right') < content.index(
            'set-selector')):
        print("  [OK] Селектор уже находится в header-right")
    else:
        # Ищем селектор в header-left и перемещаем в header-right

        # Шаблон для поиска селектора в header-left
        old_pattern = """        <div className="header-left">
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
        </div>"""

        new_left = """        <div className="header-left">
          <h1 className="header-title">GRYPHONE</h1>
        </div>"""

        # Шаблон для вставки селектора в header-right
        old_right = """        <div className="header-right">
          <HamburgerMenu />
        </div>"""

        new_right = """        <div className="header-right">
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
          <HamburgerMenu />
        </div>"""

        changes_made = []

        # Удаляем селектор из header-left
        if old_pattern in content:
            content = content.replace(old_pattern, new_left)
            changes_made.append("Удалён селектор из header-left")
        else:
            print("  [WARN] Не удалось найти селектор в header-left")

        # Добавляем селектор в header-right
        if old_right in content:
            content = content.replace(old_right, new_right)
            changes_made.append("Добавлен селектор в header-right (перед HamburgerMenu)")
        else:
            print("  [WARN] Не удалось найти header-right для вставки")

        if changes_made:
            header_jsx.write_text(content, encoding="utf-8")
            print("  [OK] Header.jsx обновлён")
            for change in changes_made:
                print(f"    • {change}")
        else:
            print("  [WARN] Изменения не применены")
    print()

    # ========================================================================
    # ШАГ 2: Проверка стилей
    # ========================================================================
    print("--- ШАГ 2: Проверка стилей ---")
    forms_css = project_root / "frontend/src/styles/forms.css"
    header_css = project_root / "frontend/src/styles/header.css"

    # Проверяем, есть ли стили для селектора
    if forms_css.exists():
        forms_content = forms_css.read_text(encoding="utf-8")
        if '.set-selector' in forms_content:
            print("  [OK] Стили .set-selector существуют в forms.css")
        else:
            print("  [WARN] Стили .set-selector не найдены")

    # Проверяем header-right
    if header_css.exists():
        header_content = header_css.read_text(encoding="utf-8")
        if '.header-right' in header_content and 'gap' in header_content:
            print("  [OK] Стили .header-right с gap существуют")
        else:
            print("  [WARN] Возможно, нужны стили для .header-right")
    print()

    # ========================================================================
    # ИТОГ
    # ========================================================================
    print("=" * 76)
    print("Готово! Селектор наборов перемещён к кнопке меню.")
    print()
    print("Структура шапки:")
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │ GRYPHONE          12:34:56          [🏢 210 ▼] ☰      │")
    print("  │ (лево)           (центр)            (право)           │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print(f"Резервная копия: {backup_jsx.name}")
    print("=" * 76)


if __name__ == "__main__":
    main()