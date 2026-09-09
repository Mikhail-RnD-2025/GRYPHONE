# -*- coding: utf-8 -*-
"""
app/db/__init__.py
==================
SQLAlchemy базовый слой (PATCH-200).

Этот модуль НЕ заменяет app/database.py — работает параллельно.
Используется в новых сервисах/репозиториях.
"""
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from app.database import db as _legacy_db  # PATCH-200.1: путь БД из легаси-слоя


# URL базы данных (SQLite, абсолютный путь) — источник истины: legacy database.py
_db_path = Path(_legacy_db.db_path).resolve()
DATABASE_URL = f"sqlite:///{_db_path}"

# Engine: check_same_thread=False нужен для Flask (потоки запросов)
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


# Импорт моделей для регистрации их в Base.metadata
from app.db import models  # noqa: E402, F401
