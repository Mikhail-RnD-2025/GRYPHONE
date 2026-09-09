# -*- coding: utf-8 -*-
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
