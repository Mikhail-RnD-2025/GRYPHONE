#!/usr/bin/env python3
"""
202. update_scripts/202_camera_service_to_repos.py
----------------------------------------------------------------------------
Перевод camera_service.py на SQLAlchemy-репозитории:
  • db.get_all_cameras()   → camera_repo.get_all()
  • db.save_cameras_list() → camera_repo.save_all()
  • db.get_all_sets()      → set_repo.get_all()
  • db.save_sets_data()    → set_repo.save()

Кэш в памяти (dataclass Camera/Set) и публичный API НЕ меняются.
Stream manager, routes, UI — продолжают работать как есть.

ЗАПУСК: python update_scripts/202_camera_service_to_repos.py
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
    f = root / "app" / "services" / "camera_service.py"

    print("=" * 76)
    print("202: camera_service → SQLAlchemy-репозитории")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-202")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "PATCH-202" in c:
        print("  [OK] Уже применён")
        return

    n = 0

    # 1. Импорт: db → repos
    old = """from app.database import db
from app.models import Camera, Set"""
    new = """from app.db.repositories import camera_repo, set_repo  # PATCH-202
from app.models import Camera, Set"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] импорт: db → camera_repo, set_repo")

    # 2. _load: камеры
    old = "        raw_cameras = db.get_all_cameras() or []"
    new = "        raw_cameras = camera_repo.get_all() or []  # PATCH-202"
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] _load: db.get_all_cameras → camera_repo.get_all")

    # 3. _load: наборы
    old = '        raw_sets = db.get_all_sets() or {"default_set": "", "sets": {}}'
    new = '        raw_sets = set_repo.get_all() or {"sets": {}}  # PATCH-202'
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] _load: db.get_all_sets → set_repo.get_all")

    # 4. save_cameras
    old = "        db.save_cameras_list( clean)"
    new = "        camera_repo.save_all( clean)  # PATCH-202"
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] save_cameras: db.save_cameras_list → camera_repo.save_all")

    # 5. _persist_cameras
    old = "        db.save_cameras_list( [c.to_dict() for c in self._cameras.values()])"
    new = "        camera_repo.save_all( [c.to_dict() for c in self._cameras.values()])  # PATCH-202"
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] _persist_cameras: db.save_cameras_list → camera_repo.save_all")

    # 6. save_sets
    old = "        db.save_sets_data( raw)"
    new = "        set_repo.save( raw)  # PATCH-202"
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] save_sets: db.save_sets_data → set_repo.save")

    if n == 6:
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] Сохранено")
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)
    else:
        print(f"  [FAIL] {n}/6 — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ camera_service переведён на репозитории!")
    print()
    print("Что НЕ изменилось:")
    print("  • Кэш (dataclass Camera/Set) — как был")
    print("  • Публичный API сервиса — stream_manager, routes работают как прежде")
    print("  • app.models.Camera/Set — dataclass-ы, не ORM")
    print()
    print("  python main.py   (проверить что всё работает)")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "refactor(sqlalchemy): camera_service uses repositories (PATCH-202)" \\')
    print('  -m "_load: camera_repo.get_all() + set_repo.get_all()" \\')
    print('  -m "save_cameras/_persist_cameras: camera_repo.save_all()" \\')
    print('  -m "save_sets: set_repo.save()" \\')
    print('  -m "public API unchanged — stream_manager/routes still work"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()