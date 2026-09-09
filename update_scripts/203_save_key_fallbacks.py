#!/usr/bin/env python3
"""
203.2 update_scripts/203_save_key_fallbacks.py
----------------------------------------------------------------------------
SetRepository.save(): принимает оба варианта ключей:
  grid_columns|max_columns, grid_rows|max_rows, camera_ids|cameras
Иначе сохранение набора из UI сбрасывало сетку на 4x3.

ЗАПУСК: python update_scripts/203_save_key_fallbacks.py
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
    f = root / "app" / "db" / "repositories.py"

    print("=" * 76)
    print("203.2: fallback-ключи в SetRepository.save()")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-2032")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    old = '                    grid_columns=set_dict.get("grid_columns", 4),\n                    grid_rows=set_dict.get("grid_rows", 3),'
    new = ('                    grid_columns=set_dict.get("grid_columns", set_dict.get("max_columns", 4)),  # PATCH-203.2\n'
           '                    grid_rows=set_dict.get("grid_rows", set_dict.get("max_rows", 3)),  # PATCH-203.2')
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] grid_columns/grid_rows: fallback на max_columns/max_rows")

    old = '                camera_ids = set_dict.get("camera_ids", [])'
    new = '                camera_ids = set_dict.get("camera_ids", set_dict.get("cameras", []))  # PATCH-203.2'
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] camera_ids: fallback на cameras")

    if n == 2:
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] Сохранено")
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)
    else:
        print(f"  [FAIL] {n}/2 — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Перезапустите сервер: python main.py")
    print("=" * 76)


if __name__ == "__main__":
    main()