#!/usr/bin/env python3
"""
140. update_scripts/140_remove_excel_import.py
----------------------------------------------------------------------------
Убирает нерабочий блок "Импорт из Excel" из SetsPage.jsx.
Импорт камер выполняется скриптом import_from_excel.py из консоли.

ЗАПУСК: python update_scripts/140_remove_excel_import.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    target = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"

    print("=" * 76)
    print("140: Убираем блок импорта Excel из SetsPage")
    print("=" * 76)
    print()

    if not target.exists():
        print("  [FAIL] SetsPage.jsx не найден")
        sys.exit(1)

    backup = target.with_suffix(".jsx.bak-140")
    backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = target.read_text(encoding="utf-8")

    if "PATCH-140" in content:
        print("  [OK] Уже применено")
        return

    changes = []

    # 1. Убираем useRef из импорта
    old_import = "import { useState, useEffect, useRef } from 'react'"
    if old_import in content:
        content = content.replace(
            old_import,
            "import { useState, useEffect } from 'react'  // PATCH-140"
        )
        changes.append("импорт useRef убран")

    # 2. Убираем fileInputRef
    ref_line = "  const fileInputRef = useRef(null)\n"
    if ref_line in content:
        content = content.replace(ref_line, "")
        changes.append("fileInputRef убран")

    # 3. Убираем функцию handleImportExcel
    fi = content.find("async function handleImportExcel")
    if fi != -1:
        line_start = content.rfind("\n", 0, fi) + 1
        fe = content.find("\n  }", fi)
        if fe != -1:
            end = fe + len("\n  }")
            content = content[:line_start] + content[end:]
            changes.append("функция handleImportExcel убрана")

    # 4. Убираем JSX-блок нижней панели
    marker = "{/* НИЖНЯЯ ПАНЕЛЬ: ИМПОРТ */}"
    i = content.find(marker)
    if i != -1:
        line_start = content.rfind("\n", 0, i) + 1
        j = content.find("</div>", i)  # первый </div> после маркера = конец панели
        if j != -1:
            end = j + len("</div>")
            content = content[:line_start] + content[end:]
            changes.append("JSX-блок импорта убран")

    print()
    print("--- Применённые изменения ---")
    for c in changes:
        print(f"  • {c}")

    if not changes:
        print("  [WARN] Ничего не найдено для удаления")

    # Проверка скобок
    print()
    print("--- Проверка синтаксиса ---")
    if content.count('{') != content.count('}') or \
       content.count('(') != content.count(')'):
        print(f"  [FAIL] Скобки: {{ {content.count('{')}/{content.count('}')} "
              f"( {content.count('(')}/{content.count(')')}")
        target.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        print("  Файл восстановлен")
        sys.exit(1)
    print("  [OK] Скобки сбалансированы")

    target.write_text(content, encoding="utf-8")
    print("  [OK] Файл сохранён")
    print()

    print("=" * 76)
    print("✅ Готово! Блок импорта Excel убран со страницы наборов.")
    print()
    print("Импорт камер по-прежнему выполняется из консоли:")
    print("  python import_from_excel.py")
    print()
    print("Пересоберите frontend:")
    print("  cd frontend && npm run build")
    print("=" * 76)


if __name__ == "__main__":
    main()