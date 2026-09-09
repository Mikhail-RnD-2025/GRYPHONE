# -*- coding: utf-8 -*-
"""
app/db/repositories.py
======================
Repository-слой (PATCH-201).

Единая точка доступа к данным для сервисов. Все методы:
  • работают внутри контекста сессии (избегают DetachedInstanceError)
  • возвращают dict/примитивы (не detached ORM-объекты)
  • инкапсулируют запросы — сервисам не нужен SQL
"""
from typing import List, Dict, Any, Optional

from app.db import get_db
from app.db.models import Camera, Setting


# ============================================================================
# CameraRepository
# ============================================================================
class CameraRepository:
    """Репозиторий камер (полный SQLAlchemy CRUD)."""

    def get_all(self) -> List[Dict[str, Any]]:
        """Возвращает список всех камер как dict."""
        with get_db() as session:
            cams = session.query(Camera).order_by(Camera.id).all()
            return [c.to_dict() for c in cams]

    def get_by_id(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Возвращает камеру по ID или None."""
        with get_db() as session:
            cam = session.query(Camera).get(camera_id)
            return cam.to_dict() if cam else None

    def count(self) -> int:
        """Количество камер."""
        with get_db() as session:
            return session.query(Camera).count()

    def save_all(self, cameras: List[Dict[str, Any]]) -> int:
        """
        PATCH-201: полная замена списка камер (совместимо с legacy save_cameras_list).

        Args:
            cameras: список dict-ов с полями камеры

        Returns:
            количество сохранённых камер
        """
        with get_db() as session:
            session.query(Camera).delete()
            for c in cameras:
                session.add(Camera(
                    id=str(c.get("id", "")).strip(),
                    name=str(c.get("name", c.get("id", ""))).strip(),
                    login=str(c.get("login", "")).strip(),
                    pass_=str(c.get("pass", "")).strip(),
                    ipaddress=str(c.get("ipaddress", "")).strip(),
                    port=str(c.get("port", "554")).strip() or "554",
                    main_url=str(c.get("main_url", "")).strip().lstrip("/"),
                    sub_url=str(c.get("sub_url", "")).strip().lstrip("/"),
                    sub2_url=str(c.get("sub2_url", "")).strip().lstrip("/"),
                    enabled=bool(c.get("enabled", True)),
                    comment=str(c.get("comment", "")).strip(),
                    audio=bool(c.get("audio", True)),
                    location=str(c.get("location", "")).strip(),
                ))
            return len(cameras)


# ============================================================================
# SettingRepository
# ============================================================================
class SettingRepository:
    """Репозиторий настроек (key-value)."""

    def get(self, key: str, default: str = "") -> str:
        """Читает значение по ключу."""
        with get_db() as session:
            row = session.query(Setting).get(key)
            return row.value if row else default

    def set(self, key: str, value: str) -> None:
        """Сохраняет значение (INSERT OR REPLACE)."""
        with get_db() as session:
            existing = session.query(Setting).get(key)
            if existing:
                existing.value = value
            else:
                session.add(Setting(key=key, value=value))

    def delete(self, key: str) -> bool:
        """Удаляет ключ. Возвращает True если был удалён."""
        with get_db() as session:
            existing = session.query(Setting).get(key)
            if existing:
                session.delete(existing)
                return True
            return False

    def all(self) -> Dict[str, str]:
        """Возвращает все настройки как dict."""
        with get_db() as session:
            rows = session.query(Setting).all()
            return {r.key: r.value for r in rows}


# ============================================================================
# SetRepository (временная реализация через legacy)
# ============================================================================
class SetRepository:
    """
    PATCH-203: репозиторий наборов (полный SQLAlchemy CRUD).
    """

    def get_all(self) -> Dict[str, Any]:
        """Возвращает {"sets": {...}} с camera_ids."""
        from app.db.models import Set
        with get_db() as session:
            sets = session.query(Set).all()
            return {
                "sets": {s.id: s.to_dict() for s in sets}
            }

    def save(self, sets_data: Dict[str, Any]) -> None:
        """Сохраняет все наборы (полная замена)."""
        from app.db.models import Set, set_cameras
        with get_db() as session:
            # Очищаем таблицы
            session.query(Set).delete()
            session.execute(set_cameras.delete())

            # Добавляем новые наборы
            for set_id, set_dict in sets_data.get("sets", {}).items():
                s = Set(
                    id=set_id,
                    name=set_dict.get("name", set_id),
                    grid_columns=set_dict.get("grid_columns", set_dict.get("max_columns", 4)),  # PATCH-203.2
                    grid_rows=set_dict.get("grid_rows", set_dict.get("max_rows", 3)),  # PATCH-203.2
                    aspect_ratio=set_dict.get("aspect_ratio", "16:9"),
                )
                session.add(s)
                session.flush()  # получаем s.id

                # Добавляем связи с камерами
                camera_ids = set_dict.get("camera_ids", set_dict.get("cameras", []))  # PATCH-203.2
                for pos, cam_id in enumerate(camera_ids):
                    session.execute(
                        set_cameras.insert().values(
                            set_id=set_id,
                            camera_id=cam_id,
                            position=pos
                        )
                    )

    def get_ids(self) -> List[str]:
        """Список ID наборов."""
        from app.db.models import Set
        with get_db() as session:
            return [s.id for s in session.query(Set).all()]


# ============================================================================
# Синглтоны для удобного импорта
# ============================================================================
camera_repo = CameraRepository()
setting_repo = SettingRepository()
set_repo = SetRepository()
