# -*- coding: utf-8 -*-
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
