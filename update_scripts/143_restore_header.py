#!/usr/bin/env python3
"""
143. update_scripts/143_restore_header.py
----------------------------------------------------------------------------
Возвращает <Header /> в SetsPage (был убран ошибочно в PATCH-138).
Header — общая навигация приложения, topbar — управление набором.

ЗАПУСК: python update_scripts/143_restore_header.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    jsx_file = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"

    print("=" * 76)
    print("143: Возврат Header в SetsPage")
    print("=" * 76)
    print()

    if not jsx_file.exists():
        print("  [FAIL] SetsPage.jsx не найден")
        sys.exit(1)

    backup = jsx_file.with_suffix(".jsx.bak-143")
    backup.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = jsx_file.read_text(encoding="utf-8")

    if "PATCH-143" in content:
        print("  [OK] Уже применён")
        return

    changes = []

    # 1. Добавить импорт Header
    old_import = "import { useState, useEffect } from 'react'\nimport '../styles/sets.css'"
    new_import = ("import { useState, useEffect } from 'react'\n"
                  "import Header from '../components/Header'\n"
                  "import '../styles/sets.css'")
    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        changes.append("импорт Header добавлен")
    else:
        print("  [FAIL] Блок импорта не найден")
        sys.exit(1)

    # 2. Обернуть sets-page в page-обёртку и добавить Header
    old_return = "  return (\n    <div className=\"sets-page\">"
    new_return = ("  return (\n"
                  "    <div className=\"page\" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>\n"
                  "      <Header />\n"
                  "      <h1 className=\"page-title\">📦 Управление наборами</h1>\n"
                  "      <div className=\"sets-page\">")
    if old_return in content:
        content = content.replace(old_return, new_return, 1)
        changes.append("Header + page-title добавлены")
    else:
        print("  [FAIL] Блок return не найден")
        sys.exit(1)

    # 3. Закрыть обёртку page в конце компонента
    old_close = "    </div>\n  )\n}"
    new_close = "      </div>\n    </div>\n  )\n}"
    if old_close in content:
        content = content.replace(old_close, new_close, 1)
        changes.append("закрытие обёртки page")
    else:
        print("  [FAIL] Блок закрытия не найден")
        sys.exit(1)

    # 4. CSS: убрать padding сверху у sets-page (Header уже даёт отступ)
    css_file = project_root / "frontend" / "src" / "styles" / "sets.css"
    css = css_file.read_text(encoding="utf-8")
    css = css.replace(
        ".sets-page {\n  display: flex;\n  flex-direction: column;\n"
        "  height: 100%;\n  min-height: 0;\n  padding: 12px;",
        "/* PATCH-143: padding сверху убран (Header даёт отступ) */\n"
        ".sets-page {\n  display: flex;\n  flex-direction: column;\n"
        "  height: auto;\n  min-height: calc(100vh - 120px);\n"
        "  padding: 0 12px 12px;",
        1
    )
    css_file.write_text(css, encoding="utf-8")
    changes.append("sets.css: адаптирован padding")

    # Проверка скобок
    print()
    print("--- Проверка синтаксиса ---")
    if content.count('{') != content.count('}') or \
       content.count('(') != content.count(')'):
        print(f"  [FAIL] Скобки не сбалансированы")
        jsx_file.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)
    print("  [OK] Скобки сбалансированы")

    jsx_file.write_text(content, encoding="utf-8")
    print()
    print("--- Применённые изменения ---")
    for c in changes:
        print(f"  • {c}")
    print()

    print("=" * 76)
    print("✅ Готово! Header возвращён.")
    print()
    print("Пересоберите:")
    print("  cd frontend && npm run build")
    print("  Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()