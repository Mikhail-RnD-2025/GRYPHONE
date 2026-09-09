# -*- coding: utf-8 -*-
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
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # PATCH-207.3.2: корень проекта
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
