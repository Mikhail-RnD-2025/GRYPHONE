#!/usr/bin/env python3
"""
219.1 update_scripts/219_1_fix_usememo_import.py
----------------------------------------------------------------------------
CamerasEditor.jsx: добавляет useMemo в импорт из 'react'

ЗАПУСК: python update_scripts/219_1_fix_usememo_import.py
"""

import sys
from pathlib import Path


def find_project_root():
    p = Path.cwd()
    while True:
        if (p / "frontend").is_dir() and (p / "update_scripts").is_dir():
            return p
        parent = p.parent
        if parent == p:
            print("[FAIL] Не найден корень проекта")
            sys.exit(1)
        p = parent


def main():
    root = find_project_root()
    f = root / "frontend" / "src" / "components" / "CamerasEditor.jsx"

    print("=" * 76)
    print("219.1: добавление useMemo в импорт")
    print("=" * 76)
    print()

    b = f.with_suffix(".jsx.bak-2191")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    old = "import { useState, useEffect, useRef } from 'react'"
    new = "import { useState, useEffect, useRef, useMemo } from 'react'  // PATCH-219.1: useMemo"

    if "useMemo } from 'react'" in c:
        print("  [OK] useMemo уже импортирован")
    elif old in c:
        c = c.replace(old, new, 1)
        f.write_text(c, encoding="utf-8")
        print("  [OK] useMemo добавлен в импорт")
    else:
        print("  [FAIL] якорь не найден")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Пересоберите:")
    print()
    print(f"  cd {root}/frontend && npm run build")
    print()
    print("Откройте /cameras (Ctrl+F5) — страница должна загрузиться")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix(cameras): add useMemo to React import (PATCH-219.1)" \\')
    print('  -m "page was blank: useMemo was used but never imported from react"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()