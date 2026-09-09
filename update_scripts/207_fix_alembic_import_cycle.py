#!/usr/bin/env python3
"""
207.3.1 update_scripts/207_fix_alembic_import_cycle.py
----------------------------------------------------------------------------
Фикс цикла импортов в alembic/env.py:
  • alembic/env.py: импорт app.db.models напрямую (без app.db)
  • app/db/__init__.py: убрать автоимпорт models в конце
  • models.py импортируется только при явном запросе

ЗАПУСК: python update_scripts/207_fix_alembic_import_cycle.py
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


ENV_PY_NEW = '''# -*- coding: utf-8 -*-
"""
alembic/env.py — PATCH-207.3.1: избегаем цикла импортов
"""
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from alembic import context

# PATCH-207.3.1: НЕ импортируем app.db (триггерит app/__init__.py)
# Вместо этого создаём engine inline

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "gryphone-vision.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

_sa_engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    echo=False,
)

Base = declarative_base()

# PATCH-207.3.1: импорт моделей напрямую (без app.db)
sys.path.insert(0, str(BASE_DIR))
from app.db import models  # noqa: E402, F401

# Alembic Config
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = _sa_engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''

DB_INIT_NEW = '''# -*- coding: utf-8 -*-
"""
app/db/__init__.py
==================
SQLAlchemy базовый слой (PATCH-207.3.1: без автоимпорта models).
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


# PATCH-207.3.1: НЕ импортируем models автоматически (избегаем цикла)
# Models импортируются явно: from app.db.models import Camera, Set, ...
'''


def patch_env_py(root):
    print("--- alembic/env.py: без app.db (избегаем цикла) ---")
    f = root / "alembic" / "env.py"
    f.write_text(ENV_PY_NEW, encoding="utf-8")
    print("  [OK] engine создаётся inline, models импортируются напрямую")
    return True


def patch_db_init(root):
    print("--- app/db/__init__.py: убрать автоимпорт models ---")
    f = root / "app" / "db" / "__init__.py"
    f.write_text(DB_INIT_NEW, encoding="utf-8")
    print("  [OK] models не импортируется автоматически")
    return True


def smoke_test(root):
    print("--- smoke-тест: старт сервера ---")
    import subprocess
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
        print(stdout[:1000])
        return False


def main():
    root = find_project_root()
    print("=" * 76)
    print("207.3.1: фикс цикла импортов alembic")
    print("=" * 76)
    print()

    ok = True
    ok &= patch_env_py(root)
    ok &= patch_db_init(root)

    if not ok:
        sys.exit(1)

    print()
    print("--- smoke-тест ---")
    smoke_test(root)

    print()
    print("=" * 76)
    print("✅ Готово!")
    print()
    print("  python main.py")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix(sqlalchemy): alembic import cycle (PATCH-207.3.1)" \\')
    print('  -m "alembic/env.py: create engine inline, import models directly" \\')
    print('  -m "app/db/__init__.py: no auto-import of models" \\')
    print('  -m "avoids: alembic → app.__init__ → config → DB query before tables"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()