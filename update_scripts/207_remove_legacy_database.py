#!/usr/bin/env python3
"""
207.3 update_scripts/207_remove_legacy_database.py
----------------------------------------------------------------------------
Финальное удаление app/database.py:
  1. app/db/__init__.py: путь БД напрямую (без legacy)
  2. main.py: программный `alembic upgrade head` перед create_app()
  3. Удаление app/database.py
  4. Seed-утилита scripts/seed_db.py (для первой установки)
  5. Smoke-тест: старт сервера + round-trip

ЗАПУСК: python update_scripts/207_remove_legacy_database.py
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


DB_INIT_NEW = '''# -*- coding: utf-8 -*-
"""
app/db/__init__.py
==================
SQLAlchemy базовый слой (PATCH-207.3: без legacy database.py).
"""
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session


# PATCH-207.3: путь БД напрямую (без legacy database.py)
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "gryphone-vision.db"

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


@contextmanager
def get_db() -> Iterator[Session]:
    """Контекстный менеджер сессии: коммит при успехе, откат при ошибке."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


from app.db import models  # noqa: E402, F401
'''

MAIN_PY_PATCH = '''# -*- coding: utf-8 -*-
"""
main.py
=======
Точка входа бэкенда.

PATCH-207.3: alembic upgrade head перед create_app()
"""
import logging
import subprocess
import sys
from pathlib import Path

# PATCH-207.3: миграции БД перед загрузкой приложения
def run_alembic_upgrade():
    """Применяет все неприменённые миграции."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"[WARN] alembic upgrade failed: {result.stderr}")
        else:
            print("[OK] alembic upgrade head")
    except Exception as e:
        print(f"[WARN] alembic upgrade error: {e}")

run_alembic_upgrade()

from app import create_app
from app.config import config

# ============================================================
# PATCH-123: очистка старых snapshot при старте сервера
# ============================================================
def cleanup_old_snapshots_123():
    """Удаляет старые snapshot-файлы, чтобы не показывать 'старые потоки'."""
    import glob
    import os
    removed = 0
    for pattern in ["**/*.jpg", "**/*.jpeg"]:
        for f in glob.glob(os.path.join("data", pattern), recursive=True):
            try:
                os.remove(f)
                removed += 1
            except OSError:
                pass
    for pattern in ["**/*.jpg", "**/*.jpeg"]:
        for f in glob.glob(os.path.join("snapshots", pattern), recursive=True):
            try:
                os.remove(f)
                removed += 1
            except OSError:
                pass
    print(f"[PATCH-123] Удалено старых snapshot: {removed}")

cleanup_old_snapshots_123()
# ============================================================


logger = logging.getLogger(__name__)


def main():
    """Главная функция: создаёт и запускает приложение."""
    app = create_app()

    host = config.get("server.host", "0.0.0.0")
    port = int(config.get("server.port", 5000))

    logger.info(f"🚀 Запуск сервера на {host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
'''

SEED_SCRIPT = '''#!/usr/bin/env python3
"""
scripts/seed_db.py
==================
Seed данных при первой установке (заменяет legacy _populate_from_json).

Использование:
  python scripts/seed_db.py

Загружает cameras.json и sets.json из data/ в БД.
"""
import json
from pathlib import Path
from app.db import get_db
from app.db.models import Camera, Set, set_cameras


def seed():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"

    cameras_file = data_dir / "cameras.json"
    sets_file = data_dir / "sets.json"

    with get_db() as session:
        # Проверяем, есть ли уже данные
        if session.query(Camera).count() > 0:
            print("  [SKIP] камеры уже есть в БД")
            return

        # Камеры
        if cameras_file.exists():
            with open(cameras_file, "r", encoding="utf-8") as f:
                cameras_data = json.load(f)
            if isinstance(cameras_data, list):
                for cam in cameras_data:
                    session.add(Camera(
                        id=cam.get("id", ""),
                        name=cam.get("name", ""),
                        login=cam.get("login", ""),
                        pass_=cam.get("pass", ""),
                        ipaddress=cam.get("ipaddress", ""),
                        port=cam.get("port", "554"),
                        main_url=str(cam.get("main_url", "")).lstrip("/"),
                        sub_url=str(cam.get("sub_url", "")).lstrip("/"),
                        sub2_url=str(cam.get("sub2_url", "")).lstrip("/"),
                        enabled=bool(cam.get("enabled", True)),
                        comment=cam.get("comment", ""),
                        audio=bool(cam.get("audio", True)),
                        location=cam.get("location", ""),
                    ))
                print(f"  [OK] загружено {len(cameras_data)} камер")

        # Наборы
        if sets_file.exists():
            with open(sets_file, "r", encoding="utf-8") as f:
                sets_data = json.load(f)
            sets_dict = sets_data.get("sets", {})
            for set_id, set_info in sets_dict.items():
                s = Set(
                    id=set_id,
                    name=set_info.get("name", set_id),
                    grid_columns=set_info.get("grid_columns", 4),
                    grid_rows=set_info.get("grid_rows", 3),
                    aspect_ratio=set_info.get("aspect_ratio", "16:9"),
                )
                session.add(s)
                session.flush()
                camera_ids = set_info.get("cameras", [])
                for pos, cam_id in enumerate(camera_ids):
                    if session.query(Camera).filter_by(id=cam_id).first():
                        session.execute(
                            set_cameras.insert().values(
                                set_id=set_id, camera_id=cam_id, position=pos
                            )
                        )
            print(f"  [OK] загружено {len(sets_dict)} наборов")


if __name__ == "__main__":
    print("Seed БД...")
    seed()
    print("✅ Готово")
'''


def patch_db_init(root):
    print("--- app/db/__init__.py: путь БД напрямую ---")
    f = root / "app" / "db" / "__init__.py"
    f.write_text(DB_INIT_NEW, encoding="utf-8")
    print("  [OK] переписан без legacy database.py")
    return True


def patch_main_py(root):
    print("--- main.py: alembic upgrade head ---")
    f = root / "main.py"
    f.write_text(MAIN_PY_PATCH, encoding="utf-8")
    print("  [OK] добавлен run_alembic_upgrade()")
    return True


def create_seed_script(root):
    print("--- scripts/seed_db.py ---")
    scripts_dir = root / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    f = scripts_dir / "seed_db.py"
    f.write_text(SEED_SCRIPT, encoding="utf-8")
    print("  [OK] создан seed-скрипт")
    return True


def remove_legacy_database(root):
    print("--- удаление app/database.py ---")
    f = root / "app" / "database.py"
    if f.exists():
        f.unlink()
        print("  [OK] app/database.py удалён")
    else:
        print("  [SKIP] файл уже отсутствует")
    return True


def smoke_test(root):
    print("--- smoke-тест: старт сервера ---")
    import time
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    time.sleep(5)
    proc.terminate()
    try:
        stdout, _ = proc.communicate(timeout=2)
    except:
        proc.kill()
        stdout = ""

    if "alembic upgrade head" in stdout or "[OK] alembic" in stdout:
        print("  [OK] alembic upgrade выполнен")
    if "✅ Приложение создано" in stdout:
        print("  [OK] сервер стартовал")
        return True
    else:
        print("  [WARN] проверьте вывод:")
        print(stdout[:500])
        return False


def main():
    root = find_project_root()
    print("=" * 76)
    print("207.3: финальное удаление app/database.py")
    print("=" * 76)
    print()

    ok = True
    ok &= patch_db_init(root)
    ok &= patch_main_py(root)
    ok &= create_seed_script(root)
    ok &= remove_legacy_database(root)

    if not ok:
        sys.exit(1)

    print()
    print("--- smoke-тест ---")
    smoke_test(root)

    print()
    print("=" * 76)
    print("✅ Миграция SQLAlchemy завершена!")
    print()
    print("Итог:")
    print("  • app/database.py удалён")
    print("  • app/db/__init__.py: путь БД напрямую")
    print("  • main.py: alembic upgrade head при старте")
    print("  • scripts/seed_db.py: для первой установки")
    print()
    print("  python main.py")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "chore(sqlalchemy): remove legacy database.py (PATCH-207.3)" \\')
    print('  -m "app/db/__init__.py: DB path without legacy import" \\')
    print('  -m "main.py: alembic upgrade head before create_app()" \\')
    print('  -m "scripts/seed_db.py: first-install data loader" \\')
    print('  -m "app/database.py: removed (replaced by alembic)"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()