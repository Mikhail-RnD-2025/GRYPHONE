# -*- coding: utf-8 -*-
"""
app/services/camera_service.py
==============================
Сервис управления камерами и наборами.

ИСПРАВЛЕНО (v27): добавлены методы update_audio и update_location.
"""
import logging
from typing import Dict, List, Optional

from app.database import db
from app.models import Camera, Set

logger = logging.getLogger(__name__)


class CameraService:
    """Управление камерами и наборами камер."""

    CAMERAS_KEY = "cameras"
    SETS_KEY = "sets"

    def __init__(self):
        self._cameras: Dict[str, Camera] = {}
        self._sets: Dict[str, Set] = {}
        self._default_set: str = ""
        self._current_set: str = ""
        self._load()

    def _load(self) -> None:
        raw_cameras = db.get(self.CAMERAS_KEY, []) or []
        self._cameras = {}
        for raw in raw_cameras:
            cam = Camera.from_raw(raw)
            if cam:
                self._cameras[cam.id] = cam

        raw_sets = db.get(self.SETS_KEY, {"default_set": "", "sets": {}}) or {}
        sets_dict = raw_sets.get("sets", {}) if isinstance(raw_sets, dict) else {}
        self._sets = {
            set_id: Set.from_raw(set_id, raw)
            for set_id, raw in sets_dict.items()
        }
        self._default_set = (
            raw_sets.get("default_set", "") if isinstance(raw_sets, dict) else ""
        )
        if not self._default_set or self._default_set not in self._sets:
            self._default_set = next(iter(self._sets), "")
        self._current_set = self._default_set

    def reload(self) -> None:
        self._load()

    def all_cameras(self) -> List[Camera]:
        return list(self._cameras.values())

    def enabled_cameras(self) -> List[Camera]:
        return [c for c in self._cameras.values() if c.enabled]

    def get_camera(self, cam_id: str) -> Optional[Camera]:
        return self._cameras.get(cam_id)

    def save_cameras(self, raw_list: List[dict]) -> int:
        self._cameras = {}
        clean = []
        for raw in raw_list:
            cam = Camera.from_raw(raw)
            if cam:
                self._cameras[cam.id] = cam
                clean.append(cam.to_dict())
        db.save(self.CAMERAS_KEY, clean)
        self._sync_workers()
        return len(clean)

    def toggle_camera(self, cam_id: str, enabled: bool) -> Optional[Camera]:
        cam = self._cameras.get(cam_id)
        if not cam:
            return None
        cam.enabled = bool(enabled)
        self._persist_cameras()
        self._sync_workers()
        return cam

    def update_comment(self, cam_id: str, comment: str) -> Optional[Camera]:
        cam = self._cameras.get(cam_id)
        if not cam:
            return None
        cam.comment = str(comment)
        self._persist_cameras()
        return cam

    # НОВОЕ (v27): обновление флага audio
    def update_audio(self, cam_id: str, audio: bool) -> Optional[Camera]:
        cam = self._cameras.get(cam_id)
        if not cam:
            return None
        cam.audio = bool(audio)
        self._persist_cameras()
        # Воркеры нужно перезапустить, чтобы применить новый флаг -an
        self._sync_workers()
        return cam

    # НОВОЕ (v27): обновление местоположения
    def update_location(self, cam_id: str, location: str) -> Optional[Camera]:
        cam = self._cameras.get(cam_id)
        if not cam:
            return None
        cam.location = str(location).strip()
        self._persist_cameras()
        # Location не влияет на воркеры, но синхронизируем для единообразия
        return cam

    def _persist_cameras(self) -> None:
        db.save(self.CAMERAS_KEY, [c.to_dict() for c in self._cameras.values()])

    def all_sets(self) -> Dict[str, Set]:
        return dict(self._sets)

    def get_set(self, set_id: str) -> Optional[Set]:
        return self._sets.get(set_id)

    def default_set_id(self) -> str:
        return self._default_set

    def current_set_id(self) -> str:
        return self._current_set

    def current_set_cameras(self) -> List[Camera]:
        current = self._sets.get(self._current_set)
        if not current:
            return []
        result = []
        for cam_id in current.camera_ids:
            cam = self._cameras.get(cam_id)
            if cam:
                result.append(cam)
        return result

    def save_sets(self, raw: dict) -> bool:
        if not isinstance(raw, dict) or "sets" not in raw:
            return False
        sets_dict = raw.get("sets", {})
        for _set_id, set_data in sets_dict.items():
            if isinstance(set_data, dict):
                set_data.setdefault("aspect_ratio", "16:9")
                set_data.setdefault("max_rows", 0)
                set_data.setdefault("max_columns", 2)
        self._sets = {
            set_id: Set.from_raw(set_id, set_data)
            for set_id, set_data in sets_dict.items()
        }
        self._default_set = raw.get("default_set", "") or self._default_set
        if self._current_set not in self._sets:
            self._current_set = self._default_set
        db.save(self.SETS_KEY, raw)
        return True

    def switch_set(self, set_id: str) -> bool:
        if not set_id or set_id not in self._sets:
            return False
        self._current_set = set_id
        self._sync_workers()
        return True

    def _sync_workers(self) -> None:
        from app.services.stream_manager import stream_manager
        stream_manager.sync(self.all_cameras())


camera_service = CameraService()
