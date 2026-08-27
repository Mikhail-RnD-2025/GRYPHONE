# -*- coding: utf-8 -*-
"""
app/cluster/models.py
=====================
Модели кластера.

ЗАГОТОВКА:
  - Node             — узел кластера (имя, роль, адрес)
  - NodeRole         — роли серверов (разделение по задачам)
  - CameraAssignment — назначение камеры на узел захвата

Сейчас все камеры обрабатывает один локальный узел, но структура
уже готова к распределению по нескольким серверам.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeRole(str, Enum):
    """Роли серверов в кластере (разделение по задачам)."""
    CONTROL = "control"      # координация, конфиг, раздача фронтенда
    CAPTURE = "capture"      # захват потоков с камер
    RELAY = "relay"          # раздача HLS-фрагментов клиентам
    RECORDER = "recorder"    # запись в архив
    ANALYTICS = "analytics"  # детекция и аналитика


@dataclass
class Node:
    """Узел кластера."""
    id: str
    role: NodeRole
    host: str = "127.0.0.1"
    port: int = 5000
    enabled: bool = True
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["role"] = self.role.value
        return d

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["Node"]:
        if not isinstance(raw, dict):
            return None
        node_id = raw.get("id")
        if not node_id:
            return None
        try:
            role = NodeRole(raw.get("role", NodeRole.CAPTURE.value))
        except ValueError:
            role = NodeRole.CAPTURE
        return cls(
            id=str(node_id).strip(),
            role=role,
            host=str(raw.get("host", "127.0.0.1")).strip(),
            port=int(raw.get("port", 5000)),
            enabled=bool(raw.get("enabled", True)),
            tags=[str(t).strip() for t in raw.get("tags", [])],
        )


@dataclass
class CameraAssignment:
    """Назначение камеры на узел захвата."""
    camera_id: str
    node_id: str
    engine: str = "auto"  # ffmpeg / gstreamer / auto

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["CameraAssignment"]:
        if not isinstance(raw, dict):
            return None
        cam_id = raw.get("camera_id")
        node_id = raw.get("node_id")
        if not cam_id or not node_id:
            return None
        return cls(
            camera_id=str(cam_id).strip(),
            node_id=str(node_id).strip(),
            engine=str(raw.get("engine", "auto")).strip(),
        )
