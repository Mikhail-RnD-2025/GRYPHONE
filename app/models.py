# -*- coding: utf-8 -*-
"""
app/models.py
=============
Модели данных приложения.

ПРОВЕРЕНО (v30): route_id используют английские суффиксы _main/_sub.
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Camera:
    """Модель камеры наблюдения."""

    id: str
    name: str
    main_url: str
    sub_url: str = ""
    enabled: bool = True
    comment: str = ""
    audio: bool = True
    location: str = ""

    @property
    def main_route_id(self) -> str:
        """Идентификатор основного потока (английский суффикс)."""
        return f"{self.id}_main"

    @property
    def sub_route_id(self) -> str:
        """Идентификатор субпотока (английский суффикс)."""
        return f"{self.id}_sub"

    @property
    def has_sub_stream(self) -> bool:
        """Проверяет, есть ли отдельный субпоток."""
        return bool(self.sub_url) and self.sub_url.strip() != "" and \
               self.sub_url != self.main_url

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["Camera"]:
        if not isinstance(raw, dict):
            return None
        cam_id = raw.get("id")
        main_url = raw.get("main_url")
        if not cam_id or not main_url:
            return None
        return cls(
            id=str(cam_id).strip(),
            name=str(raw.get("name", cam_id)).strip(),
            main_url=str(main_url).strip(),
            sub_url=str(raw.get("sub_url", "")).strip(),
            enabled=bool(raw.get("enabled", True)),
            comment=str(raw.get("comment", "")).strip(),
            audio=bool(raw.get("audio", True)),
            location=str(raw.get("location", "")).strip(),
        )


@dataclass
class Set:
    """Модель набора камер."""

    id: str
    name: str
    camera_ids: List[str] = field(default_factory=list)
    max_columns: int = 2
    max_rows: int = 0
    aspect_ratio: str = "16:9"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_raw(cls, set_id: str, raw: Dict[str, Any]) -> Optional["Set"]:
        if not isinstance(raw, dict):
            return None
        return cls(
            id=str(set_id).strip(),
            name=str(raw.get("name", set_id)).strip(),
            camera_ids=[str(cid).strip() for cid in raw.get("camera_ids", [])],
            max_columns=int(raw.get("max_columns", 2)),
            max_rows=int(raw.get("max_rows", 0)),
            aspect_ratio=str(raw.get("aspect_ratio", "16:9")).strip(),
        )


@dataclass
class Event:
    """Модель события системы."""

    source: str
    event_type: str
    severity: str = "info"
    camera_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def make(cls, source: str, event_type: str, severity: str = "info",
             camera_id: Optional[str] = None, payload: Optional[Dict] = None):
        import time
        return cls(
            source=source,
            event_type=event_type,
            severity=severity,
            camera_id=camera_id,
            payload=payload or {},
            timestamp=time.time(),
        )
