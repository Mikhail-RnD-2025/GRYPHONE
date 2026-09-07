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
    login: str = ""
    pass_: str = field(default="", metadata={"alias": "pass"})
    ipaddress: str = ""
    port: str = "554"
    main_url: str = ""
    sub_url: str = ""
    sub2_url: str = ""
    enabled: bool = True
    comment: str = ""
    audio: bool = True
    location: str = ""

    @property
    def main_route_id(self) -> str:
        return f"{self.id}_main"

    @property
    def sub_route_id(self) -> str:
        return f"{self.id}_sub"

    @property
    def has_sub_stream(self) -> bool:
        return bool(self.sub_url) and self.sub_url.strip() != "" and self.sub_url != self.main_url

    def build_url(self, stream_type: str = "main_url") -> str:
        """PATCH-184: собирает полный RTSP URL на сервере."""
        path = getattr(self, stream_type, "")
        if not path:
            return ""

        auth = ""
        if self.login:
            auth = self.login
            if self.pass_:
                auth += f":{self.pass_}"
            auth += "@"

        # Гарантируем ровно один / между портом и путём
        path = path.lstrip('/')
        return f"rtsp://{auth}{self.ipaddress}:{self.port}/{path}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if 'pass_' in d:
            d['pass'] = d.pop('pass_')
        return d


    @staticmethod
    def _split_legacy_urls(raw: Dict[str, Any]) -> Dict[str, Any]:
        """PATCH-185: если main_url/sub_url пришли полными rtsp:// — разобрать на части."""
        from urllib.parse import urlparse
        out = dict(raw)
        for key in ("main_url", "sub_url"):
            val = out.get(key) or ""
            if isinstance(val, str) and val.strip().lower().startswith("rtsp://"):
                p = urlparse(val.strip())
                out["login"] = out.get("login") or (p.username or "")
                out["pass"] = out.get("pass") or (p.password or "")
                out["ipaddress"] = out.get("ipaddress") or (p.hostname or "")
                out["port"] = out.get("port") or (str(p.port) if p.port else "554")
                path = p.path.lstrip("/")
                if p.query:
                    path += "?" + p.query
                out[key] = path
        return out

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["Camera"]:
        if not isinstance(raw, dict):
            return None
        raw = cls._split_legacy_urls(raw)  # PATCH-185
        cam_id = raw.get("id")
        ipaddress = raw.get("ipaddress")
        main_url = raw.get("main_url")
        if not cam_id or not ipaddress or not main_url:
            return None
        return cls(
            id=str(cam_id).strip(),
            name=str(raw.get("name", cam_id)).strip(),
            login=str(raw.get("login", "")).strip(),
            pass_=str(raw.get("pass", "")).strip(),
            ipaddress=str(ipaddress).strip(),
            port=str(raw.get("port", "554")).strip(),
            main_url=str(main_url).strip().lstrip('/'),  # PATCH-184: обрезка ведущего /
            sub_url=str(raw.get("sub_url", "")).strip().lstrip('/'),
            sub2_url=str(raw.get("sub2_url", "")).strip().lstrip('/'),
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
