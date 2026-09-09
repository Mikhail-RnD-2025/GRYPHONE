#!/usr/bin/env python3
"""
207.2 update_scripts/207_fix_alembic_stamp.py
----------------------------------------------------------------------------
Фикс Alembic baseline:
  1. Удаляет некорректную миграцию a240c03a7164_baseline.py
  2. Добавляет модель Event в app/db/models.py (есть в schema.sql)
  3. Создаёт ПУСТУЮ миграцию baseline
  4. Запускает `alembic stamp head` (помечает БД как baseline)

Это безопаснее, чем autogenerate, который пытается пересоздать констрейнты.

ЗАПУСК: python update_scripts/207_fix_alembic_stamp.py
"""

import sys
import subprocess
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


EVENT_MODEL = '''

# ----------------------------------------------------------------------------
# Event (системные события — PATCH-207.2)
# ----------------------------------------------------------------------------
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(String, nullable=False)  # Unix timestamp
    source = Column(String, nullable=False)  # 'camera', 'worker', 'system', 'user'
    camera_id = Column(String, ForeignKey("cameras.id", ondelete="SET NULL"))
    node_id = Column(String)
    event_type = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="info")
    payload = Column(String)  # JSON
    acknowledged = Column(Integer, default=0)
    sent_to_psim = Column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<Event id={self.id} type={self.event_type}>"
'''


def remove_bad_migration(root):
    print("--- удаление некорректной миграции ---")
    versions = root / "alembic" / "versions"
    bad_files = list(versions.glob("*baseline*.py"))
    if not bad_files:
        print("  [OK] некорректных миграций нет")
        return True
    for f in bad_files:
        f.unlink()
        print(f"  [OK] удалена: {f.name}")
    return True


def add_event_model(root):
    print("--- app/db/models.py: + Event ---")
    f = root / "app" / "db" / "models.py"
    c = f.read_text(encoding="utf-8")

    if "class Event(Base):" in c:
        print("  [OK] Event уже есть")
        return True

    # Добавляем импорт Integer (если нет)
    if "Integer" not in c.split("from sqlalchemy import")[1].split("\n")[0]:
        c = c.replace(
            "from sqlalchemy import (\n    Column, String, Integer, Boolean, ForeignKey, Table\n)",
            "from sqlalchemy import (\n    Column, String, Integer, Boolean, ForeignKey, Table\n)"
        )

    # Добавляем модель Event в конец
    c = c.rstrip() + EVENT_MODEL
    f.write_text(c, encoding="utf-8")
    print("  [OK] Event добавлен")
    return True


def create_empty_baseline(root):
    print("--- создание пустой миграции baseline ---")
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "revision", "-m", "baseline"],
        cwd=str(root), capture_output=True, text=True
    )
    if res.returncode != 0:
        print(f"  [FAIL] {res.stderr}")
        return False
    print(f"  [OK] {res.stdout.strip()}")
    return True


def stamp_head(root):
    print("--- alembic stamp head ---")
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "stamp", "head"],
        cwd=str(root), capture_output=True, text=True
    )
    if res.returncode != 0:
        print(f"  [FAIL] {res.stderr}")
        return False
    print("  [OK] БД помечена как baseline")
    return True


def verify_current(root):
    print("--- alembic current ---")
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        cwd=str(root), capture_output=True, text=True
    )
    print(f"  current: {res.stdout.strip()}")
    if "baseline" in res.stdout:
        print("  [OK] baseline применён")
        return True
    return False


def main():
    root = find_project_root()
    print("=" * 76)
    print("207.2: Fix Alembic — Stamp Strategy")
    print("=" * 76)
    print()

    ok = True
    ok &= remove_bad_migration(root)
    ok &= add_event_model(root)
    ok &= create_empty_baseline(root)
    ok &= stamp_head(root)
    ok &= verify_current(root)

    if not ok:
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Alembic baseline готов!")
    print()
    print("Теперь:")
    print("  • alembic current → показывает baseline")
    print("  • Любые изменения ORM → alembic revision --autogenerate")
    print("  • Применение → alembic upgrade head")
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat(sqlalchemy): alembic baseline + Event model (PATCH-207.2)" \\')
    print('  -m "alembic stamp head (safe baseline for existing DB)" \\')
    print('  -m "app/db/models.py: + Event model (matches schema.sql)" \\')
    print('  -m "alembic/versions/*_baseline.py: empty revision"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()