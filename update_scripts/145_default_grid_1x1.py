#!/usr/bin/env python3
"""
145. update_scripts/145_default_grid_1x1.py
----------------------------------------------------------------------------
Дефолтная сетка набора = 1x1 (вместо 8x7 / 4x6):
  • backend create_set: дефолты 1/1
  • frontend createSet: отправляет 1/1
  • normalizeSet: fallback 1/1
  • рендер: fallback 1/1

ЗАПУСК: python update_scripts/145_default_grid_1x1.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    jsx_file = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"
    api_file = project_root / "app" / "routes" / "api.py"

    print("=" * 76)
    print("145: Дефолтная сетка 1x1")
    print("=" * 76)
    print()

    # --- FRONTEND ---
    print("--- SetsPage.jsx ---")
    backup_jsx = jsx_file.with_suffix(".jsx.bak-145")
    backup_jsx.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_jsx.name}")

    content = jsx_file.read_text(encoding="utf-8")
    n = 0

    repls = [
        ("body: JSON.stringify({ name, max_rows: 4, max_columns: 6 })",
         "body: JSON.stringify({ name, max_rows: 1, max_columns: 1 })  // PATCH-145"),
        ("max_rows: parseInt(raw.max_rows) || 7,    // PATCH-144: единый дефолт",
         "max_rows: parseInt(raw.max_rows) || 1,    // PATCH-145: дефолт 1x1"),
        ("max_columns: parseInt(raw.max_columns) || 8,",
         "max_columns: parseInt(raw.max_columns) || 1,"),
        ("const maxCols = activeSet ? activeSet.max_columns : 8",
         "const maxCols = activeSet ? activeSet.max_columns : 1  // PATCH-145"),
        ("const maxRows = activeSet ? activeSet.max_rows : 7",
         "const maxRows = activeSet ? activeSet.max_rows : 1"),
    ]
    for old, new in repls:
        if old in content:
            content = content.replace(old, new, 1)
            n += 1
            print(f"  [OK] {old[:50]}...")

    if n == 0:
        print("  [FAIL] Ничего не заменено — откат")
        sys.exit(1)

    if content.count('{') != content.count('}') or \
       content.count('(') != content.count(')'):
        print("  [FAIL] Скобки не сбалансированы — откат")
        jsx_file.write_text(backup_jsx.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    jsx_file.write_text(content, encoding="utf-8")
    print(f"  [OK] Сохранено ({n} замен)")

    # --- BACKEND ---
    print()
    print("--- api.py ---")
    backup_api = api_file.with_suffix(".py.bak-145")
    backup_api.write_text(api_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_api.name}")

    acontent = api_file.read_text(encoding="utf-8")
    m = 0

    arepls = [
        ('max_rows = min(max(int(data.get("max_rows", 7)), 1), 32)',
         'max_rows = min(max(int(data.get("max_rows", 1)), 1), 32)  # PATCH-145'),
        ('max_columns = min(max(int(data.get("max_columns", 8)), 1), 32)',
         'max_columns = min(max(int(data.get("max_columns", 1)), 1), 32)'),
    ]
    for old, new in arepls:
        if old in acontent:
            acontent = acontent.replace(old, new, 1)
            m += 1
            print(f"  [OK] {old[:50]}...")

    if m == 0:
        print("  [FAIL] Ничего не заменено — откат")
        sys.exit(1)

    try:
        compile(acontent, str(api_file), "exec")
    except SyntaxError as e:
        print(f"  [FAIL] Синтаксис: {e} — откат")
        api_file.write_text(backup_api.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    api_file.write_text(acontent, encoding="utf-8")
    print(f"  [OK] Сохранено ({m} замен)")

    print()
    print("=" * 76)
    print("✅ Готово! Дефолтная сетка = 1x1 во всех местах.")
    print()
    print("  cd frontend && npm run build")
    print("  перезапуск: python main.py")
    print("=" * 76)


if __name__ == "__main__":
    main()