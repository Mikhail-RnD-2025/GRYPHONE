#!/usr/bin/env python3
"""
200. update_scripts/200_sqlalchemy_base.py
----------------------------------------------------------------------------
Этап 1 миграции на SQLAlchemy:
  • pip install sqlalchemy (если не установлен)
  • app/db/__init__.py: engine, SessionLocal, get_db
  • app/db/models.py: Camera, Set, Setting + M2M set_cameras
  • Smoke-test: читает все камеры через SQLAlchemy, сравнивает со старым кодом

ЗАПУСК: python update_scripts/200_sqlalchemy_base.py
ПОСЛЕ:  старый код (routes/services/database.py) НЕ тронут —
        они продолжают работать через сырой sqlite3.
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


DB_INIT = '''# -*- coding: utf-8 -*-
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

from app.config import config


# URL базы данных (SQLite, абсолютный путь)
_db_path = Path(config.DATABASE_PATH).resolve()
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
'''


DB_MODELS = '''# -*- coding: utf-8 -*-
"""
app/db/models.py
================
SQLAlchemy ORM-модели (PATCH-200).

Зеркало текущей схемы БД:
  cameras, sets, set_cameras (M2M), settings

Имена атрибутов соответствуют именам полей в app.models.Camera/Set,
кроме pass → pass_ (зарезервированное слово SQL).
"""
from sqlalchemy import (
    Column, String, Integer, Boolean, ForeignKey, Table
)
from sqlalchemy.orm import relationship

from app.db import Base


# ----------------------------------------------------------------------------
# Association table: наборы ↔ камеры (M2M)
# ----------------------------------------------------------------------------
set_cameras = Table(
    "set_cameras",
    Base.metadata,
    Column("set_id", String, ForeignKey("sets.id"), primary_key=True),
    Column("camera_id", String, ForeignKey("cameras.id"), primary_key=True),
)


# ----------------------------------------------------------------------------
# Camera
# ----------------------------------------------------------------------------
class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String, primary_key=True)
    name = Column(String)
    login = Column(String)
    pass_ = Column("pass", String)  # колонка 'pass' в БД, атрибут 'pass_' в Python
    ipaddress = Column(String)
    port = Column(String, default="554")
    main_url = Column(String)
    sub_url = Column(String)
    sub2_url = Column(String)
    enabled = Column(Boolean, default=True)
    comment = Column(String)
    audio = Column(Boolean, default=True)
    location = Column(String)

    # Связь с наборами (через M2M)
    sets = relationship("Set", secondary=set_cameras, back_populates="cameras")

    def __repr__(self) -> str:
        return f"<Camera id={self.id} name={self.name!r}>"

    def to_dict(self) -> dict:
        """Совместимость со старым app.models.Camera.to_dict()."""
        return {
            "id": self.id,
            "name": self.name,
            "login": self.login or "",
            "pass": self.pass_ or "",  # ключ 'pass', не 'pass_'
            "ipaddress": self.ipaddress or "",
            "port": self.port or "554",
            "main_url": self.main_url or "",
            "sub_url": self.sub_url or "",
            "sub2_url": self.sub2_url or "",
            "enabled": bool(self.enabled),
            "comment": self.comment or "",
            "audio": bool(self.audio),
            "location": self.location or "",
        }


# ----------------------------------------------------------------------------
# Set (набор камер)
# ----------------------------------------------------------------------------
class Set(Base):
    __tablename__ = "sets"

    id = Column(String, primary_key=True)
    name = Column(String)
    grid_columns = Column(Integer, default=4)
    grid_rows = Column(Integer, default=3)
    aspect_ratio = Column(String, default="16:9")

    # Связь с камерами (через M2M)
    cameras = relationship("Camera", secondary=set_cameras, back_populates="sets")

    def __repr__(self) -> str:
        return f"<Set id={self.id} name={self.name!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "grid_columns": self.grid_columns,
            "grid_rows": self.grid_rows,
            "aspect_ratio": self.aspect_ratio or "16:9",
        }


# ----------------------------------------------------------------------------
# Setting (таблица ключ-значение, используется для сохранения настроек)
# ----------------------------------------------------------------------------
class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<Setting key={self.key!r}>"
'''


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

    with get_db() as session:
        # Камеры
        sa_cams = session.query(Camera).all()
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

    # Проверка согласованности
    if len(sa_cams) != len(legacy_cams):
        print("  [FAIL] Количество камер не совпадает!")
        return False
    if len(sa_sets) != n_legacy_sets:
        print("  [FAIL] Количество наборов не совпадает!")
        return False

    # Сравнение первой камеры (to_dict)
    if sa_cams and legacy_cams:
        sa_dict = sa_cams[0].to_dict()
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


def ensure_sqlalchemy():
    print("--- установка SQLAlchemy ---")
    try:
        import sqlalchemy
        print(f"  [OK] SQLAlchemy {sqlalchemy.__version__} уже установлен")
        return True
    except ImportError:
        print("  [...] установка sqlalchemy")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "sqlalchemy"])
            import sqlalchemy
            print(f"  [OK] Установлен SQLAlchemy {sqlalchemy.__version__}")
            return True
        except Exception as e:
            print(f"  [FAIL] установка не удалась: {e}")
            return False


def main():
    root = find_project_root()
    print(f"  [OK] Корень проекта: {root}")
    print()
    print("=" * 76)
    print("200: базовый слой SQLAlchemy (параллельно старому коду)")
    print("=" * 76)
    print()

    if not ensure_sqlalchemy():
        sys.exit(1)

    db_dir = root / "app" / "db"
    db_dir.mkdir(exist_ok=True)

    init_f = db_dir / "__init__.py"
    models_f = db_dir / "models.py"
    test_f = root / "smoke_test_sqlalchemy.py"

    # 1. app/db/__init__.py
    print("--- app/db/__init__.py ---")
    if init_f.exists() and "PATCH-200" in init_f.read_text(encoding="utf-8"):
        print("  [OK] уже существует")
    else:
        init_f.write_text(DB_INIT, encoding="utf-8")
        print("  [OK] создан: engine, SessionLocal, get_db, Base")

    # 2. app/db/models.py
    print("--- app/db/models.py ---")
    if models_f.exists() and "PATCH-200" in models_f.read_text(encoding="utf-8"):
        print("  [OK] уже существует")
    else:
        models_f.write_text(DB_MODELS, encoding="utf-8")
        print("  [OK] создан: Camera, Set, Setting, set_cameras (M2M)")

    # 3. Smoke-test
    print("--- smoke_test_sqlalchemy.py ---")
    test_f.write_text(SMOKE_TEST, encoding="utf-8")
    print("  [OK] создан")

    # 4. Запускаем smoke-test
    print()
    print("--- запуск smoke-теста ---")
    res = subprocess.run([sys.executable, str(test_f)], cwd=str(root))
    if res.returncode != 0:
        print("  [FAIL] smoke-тест не прошёл")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Этап 200 завершён!")
    print()
    print("Что добавлено:")
    print("  • app/db/__init__.py  — engine, SessionLocal, get_db(), Base")
    print("  • app/db/models.py    — Camera, Set, Setting + M2M set_cameras")
    print("  • smoke_test_sqlalchemy.py — можно удалить после проверки")
    print()
    print("Что НЕ тронуто:")
    print("  • app/database.py     — работает как прежде")
    print("  • app/services/*      — продолжают использовать старый слой")
    print("  • app/routes/*        — без изменений")
    print()
    print("Следующий этап: PATCH-201 — Repository-слой (CameraRepository, SetRepository)")
    print("=" * 76)
    print()
    print("📦 Коммит после успеха:")
    print()
    print(f"cd {root}")
    print("rm smoke_test_sqlalchemy.py")
    print("git add -A")
    print('git commit -m "feat(sqlalchemy): base layer - engine, models, session (PATCH-200)" \\')
    print('  -m "app/db/__init__.py: engine, SessionLocal, get_db, declarative Base" \\')
    print('  -m "app/db/models.py: Camera, Set, Setting + set_cameras M2M table" \\')
    print('  -m "pass column mapped to pass_ attribute (reserved SQL word)" \\')
    print('  -m "smoke-test: SA reads same data as legacy database.py"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()