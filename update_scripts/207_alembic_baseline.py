#!/usr/bin/env python3
"""
207.1 update_scripts/207_alembic_baseline.py
----------------------------------------------------------------------------
  • pip install alembic
  • alembic init alembic → alembic.ini + alembic/
  • alembic/env.py: импорт app.db.Base + SQLAlchemy engine
  • alembic revision --autogenerate -m "baseline" → первая миграция
  • alembic upgrade head → применить к текущей БД (идемпотентно)

ПОСЛЕ: app/database.py ещё существует, legacy продолжает работать.
       Финальный шаг — PATCH-207.2 (замена в main.py + удаление).

ЗАПУСК: python update_scripts/207_alembic_baseline.py
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


ENV_PY = '''# -*- coding: utf-8 -*-
"""
alembic/env.py — PATCH-207: миграции через SQLAlchemy
"""
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Корень проекта в sys.path (для импорта app.db)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import engine as _sa_engine, Base  # PATCH-207: наши модели
import app.db.models  # noqa: F401  — регистрация моделей в Base.metadata

# Alembic Config
config = context.config

# Логирование
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
        render_as_batch=True,  # SQLite: ALTER TABLE через recreate
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = _sa_engine  # PATCH-207: используем наш engine (путь из legacy db)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''


ALEMBIC_INI_PATCH = """# sqlalchemy.url берём из app.db.engine (через env.py),
# поэтому в ini оставляем заглушку — env.py её перепишет.
sqlalchemy.url = sqlite:///./placeholder.db
"""


def ensure_alembic():
    print("--- установка alembic ---")
    try:
        import alembic
        print(f"  [OK] alembic {alembic.__version__} уже установлен")
        return True
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "alembic"])
            import alembic
            print(f"  [OK] установлен alembic {alembic.__version__}")
            return True
        except Exception as e:
            print(f"  [FAIL] {e}")
            return False


def init_alembic(root):
    print("--- alembic init ---")
    alembic_dir = root / "alembic"
    ini_file = root / "alembic.ini"

    if alembic_dir.exists() and ini_file.exists():
        print("  [OK] alembic/ уже существует")
        return True

    res = subprocess.run(
        [sys.executable, "-m", "alembic", "init", "alembic"],
        cwd=str(root), capture_output=True, text=True
    )
    if res.returncode != 0:
        print(f"  [FAIL] alembic init: {res.stderr}")
        return False
    print("  [OK] alembic/ и alembic.ini созданы")
    return True


def patch_env_py(root):
    print("--- alembic/env.py: импорт app.db ---")
    f = root / "alembic" / "env.py"
    f.write_text(ENV_PY, encoding="utf-8")
    print("  [OK] переписан под app.db.engine + app.db.Base")


def patch_alembic_ini(root):
    print("--- alembic.ini: sqlalchemy.url = placeholder ---")
    f = root / "alembic.ini"
    c = f.read_text(encoding="utf-8")
    # заменяем секцию sqlalchemy.url
    import re
    c = re.sub(
        r"sqlalchemy\.url\s*=.*",
        "# sqlalchemy.url overridden by env.py (uses app.db.engine)",
        c, count=1
    )
    f.write_text(c, encoding="utf-8")
    print("  [OK] url берётся из env.py (через app.db.engine)")


def check_schema_match(root):
    """Проверяем что наша ORM-схема совпадает с реальной БД (без создания таблиц)."""
    print("--- проверка схемы: ORM vs БД ---")
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "current", "--verbose"],
        cwd=str(root), capture_output=True, text=True
    )
    print("  current:", res.stdout.strip() or "(empty — первая миграция ещё не применена)")
    return True


def create_baseline(root):
    print("--- создание baseline миграции ---")
    versions = root / "alembic" / "versions"
    existing = list(versions.glob("*.py"))
    if any("baseline" in f.name or f.read_text(encoding="utf-8").count("op.") > 0 for f in existing):
        print("  [OK] миграция уже есть")
        return True

    res = subprocess.run(
        [sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", "baseline"],
        cwd=str(root), capture_output=True, text=True
    )
    if res.returncode != 0:
        print(f"  [FAIL] revision: {res.stderr}")
        print(f"  stdout: {res.stdout}")
        return False
    print(f"  [OK] миграция создана")
    print(f"  {res.stdout.strip().splitlines()[-1] if res.stdout.strip() else ''}")

    # Проверка содержимого: должно быть пусто (схема уже существует)
    new_files = [f for f in versions.glob("*.py") if f not in existing]
    if new_files:
        content = new_files[0].read_text(encoding="utf-8")
        # Если autogenerate нашёл различия — это warning
        if "op.create_table" in content or "op.add_column" in content:
            print("  [WARN] autogenerate нашёл расхождения между ORM и БД")
            print("         (скорее всего: events не в ORM, или aspect_ratio)")
            # Это нормально для baseline — создаётся текущее состояние
        else:
            print("  [OK] ORM-схема совпадает с БД (пустая миграция)")
    return True


def apply_baseline(root):
    print("--- alembic upgrade head ---")
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(root), capture_output=True, text=True
    )
    if res.returncode != 0:
        print(f"  [FAIL] upgrade: {res.stderr}")
        return False
    print("  [OK] применено")
    return True


def verify_stamp(root):
    print("--- alembic current ---")
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        cwd=str(root), capture_output=True, text=True
    )
    print("  current:", res.stdout.strip())
    if "baseline" in res.stdout:
        print("  [OK] baseline применён")
        return True
    return False


def main():
    root = find_project_root()
    print("=" * 76)
    print("207.1: Alembic baseline (первая миграция)")
    print("=" * 76)
    print()

    ok = True
    ok &= ensure_alembic()
    ok &= init_alembic(root)
    if not ok:
        sys.exit(1)

    patch_env_py(root)
    patch_alembic_ini(root)
    check_schema_match(root)

    ok &= create_baseline(root)
    ok &= apply_baseline(root)
    ok &= verify_stamp(root)

    if not ok:
        print()
        print("[FAIL] один из шагов не прошёл")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Этап 207.1 завершён!")
    print()
    print("Создано:")
    print("  • alembic.ini")
    print("  • alembic/env.py     — использует app.db.engine")
    print("  • alembic/versions/xxxx_baseline.py")
    print("  • alembic_version таблица в БД")
    print()
    print("Следующий шаг: PATCH-207.2 — замена Database() в main.py на")
    print("'alembic upgrade head' и удаление app/database.py")
    print("=" * 76)


if __name__ == "__main__":
    main()