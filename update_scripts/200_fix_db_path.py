#!/usr/bin/env python3
"""
200.1 update_scripts/200_fix_db_path.py
----------------------------------------------------------------------------
app/db/__init__.py: берёт путь БД из app.database.db.db_path
вместо несуществующего config.DATABASE_PATH

ЗАПУСК: python update_scripts/200_fix_db_path.py
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
    f = root / "app" / "db" / "__init__.py"

    print("=" * 76)
    print("200.1: путь БД из легаси-слоя (db.db_path)")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-200")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    old = """from app.config import config


# URL базы данных (SQLite, абсолютный путь)
_db_path = Path(config.DATABASE_PATH).resolve()"""

    new = """from app.database import db as _legacy_db  # PATCH-200.1: путь БД из легаси-слоя


# URL базы данных (SQLite, абсолютный путь) — источник истины: legacy database.py
_db_path = Path(_legacy_db.db_path).resolve()"""

    if old in c:
        c = c.replace(old, new, 1)
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] путь БД берётся из db.db_path")
        except SyntaxError as e:
            print(f"  [FAIL] {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)
    else:
        print("  [FAIL] якорь не найден — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("  Повторный запуск smoke-теста:")
    import subprocess
    res = subprocess.run([sys.executable, str(root / "smoke_test_sqlalchemy.py")], cwd=str(root))
    if res.returncode != 0:
        print("  [FAIL] smoke-тест не прошёл")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Этап 200 завершён!")
    print()
    print("📦 Коммит:")
    print()
    print(f"cd {root}")
    print("rm smoke_test_sqlalchemy.py")
    print("git add -A")
    print('git commit -m "feat(sqlalchemy): base layer - engine, models, session (PATCH-200)" \\')
    print('  -m "app/db/__init__.py: engine, SessionLocal, get_db, declarative Base" \\')
    print('  -m "app/db/models.py: Camera, Set, Setting + set_cameras M2M table" \\')
    print('  -m "pass column mapped to pass_ attribute (reserved SQL word)" \\')
    print('  -m "db path taken from legacy database.py (single source of truth)"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()