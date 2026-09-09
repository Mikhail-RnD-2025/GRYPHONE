# -*- coding: utf-8 -*-
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
