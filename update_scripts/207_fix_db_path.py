#!/usr/bin/env python3
"""
207.3.2 update_scripts/207_fix_db_path.py
----------------------------------------------------------------------------
  • app/db/__init__.py: BASE_DIR = parent.parent.parent (корень проекта)
  • удаляет БД-призрак app/database/gryphone-vision.db и каталог app/database
  • верификация: путь + counts из боевой БД

ЗАПУСК: python update_scripts/207_fix_db_path.py
"""

import sys
import sqlite3
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
    print("=" * 76)
    print("207.3.2: фикс пути БД (parent.parent.parent)")
    print("=" * 76)
    print()

    # 1. Фикс пути
    f = root / "app" / "db" / "__init__.py"
    b = f.with_suffix(".py.bak-20732")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    old = """BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database\""""
    new = """BASE_DIR = Path(__file__).resolve().parent.parent.parent  # PATCH-207.3.2: корень проекта
DATABASE_DIR = BASE_DIR / "database\""""

    if old in c:
        c = c.replace(old, new, 1)
        f.write_text(c, encoding="utf-8")
        print("  [OK] BASE_DIR: parent.parent.parent (корень проекта)")
    elif "parent.parent.parent" in c:
        print("  [OK] путь уже исправлен")
    else:
        print("  [FAIL] якорь не найден — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # 2. Удаляем БД-призрак
    stray_dir = root / "app" / "database"
    stray_db = stray_dir / "gryphone-vision.db"
    if stray_db.exists():
        stray_db.unlink()
        print(f"  [OK] удалена БД-призрак: {stray_db}")
    try:
        if stray_dir.is_dir() and not any(stray_dir.iterdir()):
            stray_dir.rmdir()
            print("  [OK] удалён пустой каталог app/database")
    except OSError:
        pass

    # 3. Верификация
    print()
    print("--- верификация ---")
    sys.path.insert(0, str(root))
    from app.db import DATABASE_PATH
    print(f"  путь БД: {DATABASE_PATH}")
    expected = root / "database" / "gryphone-vision.db"
    if Path(DATABASE_PATH).resolve() != expected.resolve():
        print("  [FAIL] путь всё ещё неверный!")
        sys.exit(1)
    conn = sqlite3.connect(str(DATABASE_PATH))
    n_settings = conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
    n_cameras = conn.execute("SELECT COUNT(*) FROM cameras").fetchone()[0]
    n_sets = conn.execute("SELECT COUNT(*) FROM sets").fetchone()[0]
    n_ver = conn.execute("SELECT COUNT(*) FROM alembic_version").fetchone()[0]
    conn.close()
    print(f"  settings: {n_settings}, cameras: {n_cameras}, sets: {n_sets}, alembic_version: {n_ver}")
    if n_cameras != 24 or n_settings != 1:
        print("  [FAIL] боевая БД повреждена?")
        sys.exit(1)
    print("  [OK] боевая БД цела")

    print()
    print("=" * 76)
    print("✅ Готово! Запустите сервер вручную:")
    print("  python main.py")
    print()
    print("Ожидаемо:")
    print("  [OK] alembic upgrade head")
    print("  [PATCH-123] Удалено старых snapshot: 0")
    print("  ✅ Приложение создано и настроено")
    print("=" * 76)


if __name__ == "__main__":
    main()