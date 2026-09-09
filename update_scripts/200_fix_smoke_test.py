#!/usr/bin/env python3
"""
200.2 update_scripts/200_fix_smoke_test.py
----------------------------------------------------------------------------
Исправляет smoke_test_sqlalchemy.py: вызывает to_dict() ВНУТРИ with-блока,
пока сессия ещё открыта (иначе DetachedInstanceError).

ЗАПУСК: python update_scripts/200_fix_smoke_test.py
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


SMOKE_TEST = '''"""Smoke-тест SQLAlchemy слоя (временный, удалить после проверки)."""
import sys
sys.path.insert(0, ".")

from app.db import get_db
from app.db.models import Camera, Set, Setting
from app.database import db as legacy_db


def main():
    print("=" * 70)
    print("SQLAlchemy smoke-test")
    print("=" * 70)

    # PATCH-200.2: читаем всё ВНУТРИ with-блока (иначе DetachedInstanceError)
    with get_db() as session:
        # Камеры
        sa_cams = session.query(Camera).all()
        sa_dicts = [c.to_dict() for c in sa_cams]  # PATCH-200.2: to_dict() пока сессия открыта
        legacy_cams = legacy_db.get_all_cameras() or []

        print(f"  SQLAlchemy: {len(sa_cams)} камер")
        print(f"  Legacy:     {len(legacy_cams)} камер")

        # Наборы
        sa_sets = session.query(Set).all()
        legacy_sets = legacy_db.get_all_sets() or {"sets": {}}
        n_legacy_sets = len(legacy_sets.get("sets", {}))

        print(f"  SQLAlchemy: {len(sa_sets)} наборов")
        print(f"  Legacy:     {n_legacy_sets} наборов")

        # Settings
        sa_settings = session.query(Setting).all()
        print(f"  SQLAlchemy: {len(sa_settings)} настроек")

    # Проверка согласованности (вне with — используем уже прочитанные данные)
    if len(sa_cams) != len(legacy_cams):
        print("  [FAIL] Количество камер не совпадает!")
        return False
    if len(sa_sets) != n_legacy_sets:
        print("  [FAIL] Количество наборов не совпадает!")
        return False

    # Сравнение первой камеры (to_dict уже вызван внутри with)
    if sa_dicts and legacy_cams:
        sa_dict = sa_dicts[0]
        lg_dict = legacy_cams[0]
        keys = set(sa_dict.keys()) & set(lg_dict.keys())
        mismatches = [k for k in keys if sa_dict[k] != lg_dict[k]]
        if mismatches:
            print(f"  [WARN] Расхождения по ключам: {mismatches}")
            for k in mismatches[:3]:
                print(f"       {k}: SA={sa_dict[k]!r}  legacy={lg_dict[k]!r}")
        else:
            print("  [OK] to_dict() совпадает для первой камеры")

    print("=" * 70)
    print("✅ SQLAlchemy слой работает и согласован со старой БД")
    print("=" * 70)
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
'''


def main():
    root = find_project_root()
    f = root / "smoke_test_sqlalchemy.py"

    print("=" * 76)
    print("200.2: to_dict() внутри with-блока сессии")
    print("=" * 76)
    print()

    f.write_text(SMOKE_TEST, encoding="utf-8")
    print("  [OK] smoke_test_sqlalchemy.py переписан")

    print()
    print("  Повторный запуск smoke-теста:")
    import subprocess
    res = subprocess.run([sys.executable, str(f)], cwd=str(root))
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
    print('  -m "db path taken from legacy database.py (single source of truth)" \\')
    print('  -m "smoke-test: SA reads same data as legacy database.py"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()