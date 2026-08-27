#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 27: НОВЫЕ ПОЛЯ КАМЕРЫ (audio, location)
#  ------------------------------------------------------------
#  Добавляет в модель камеры два новых поля:
#    - audio (bool):  включать ли аудио при захвате потока
#    - location (str): текстовое описание местоположения
#
#  Что делает:
#    1. app/models.py             — новые поля в модели Camera
#    2. app/workers/hls_worker.py — флаг -an при audio=false
#    3. app/routes/api.py         — эндпоинты для audio/location
#    4. app/services/camera_service.py — методы обновления полей
#    5. frontend/src/api.js       — клиентские функции
#    6. frontend/src/components/CameraCard.jsx — отображение полей
#    7. frontend/src/components/ContextMenu.jsx — редактирование
#    8. migrate_add_fields.py     — миграция существующих камер
#
#  Запуск:   bash 27_camera_fields.sh
#  После:    python migrate_add_fields.py && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. app/models.py — добавлены поля audio и location
# ============================================================
cat > "$PROJECT_DIR/app/models.py" << 'PYEOF_MODELS'
# -*- coding: utf-8 -*-
"""
app/models.py
=============
Модели данных приложения.

ИСПРАВЛЕНО (v27): в модель Camera добавлены поля:
  - audio (bool):   включать ли аудио при захвате потока
  - location (str): текстовое описание местоположения
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
    # НОВОЕ (v27):
    audio: bool = True
    location: str = ""

    @property
    def main_route_id(self) -> str:
        """Идентификатор основного потока."""
        return f"{self.id}_основной"

    @property
    def sub_route_id(self) -> str:
        """Идентификатор субпотока."""
        return f"{self.id}_дополнительный"

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация камеры в словарь."""
        return asdict(self)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["Camera"]:
        """Создаёт камеру из "сырого" словаря.

        ИСПРАВЛЕНО (v27): поддержка новых полей audio и location
        с дефолтными значениями для старых данных.
        """
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
            # НОВОЕ (v27): значения по умолчанию для старых данных.
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
        """Сериализация набора в словарь."""
        return asdict(self)

    @classmethod
    def from_raw(cls, set_id: str, raw: Dict[str, Any]) -> Optional["Set"]:
        """Создаёт набор из "сырого" словаря."""
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
PYEOF_MODELS
echo "  ✔ app/models.py (добавлены поля audio и location)"

# ============================================================
# 2. app/workers/hls_worker.py — флаг -an при audio=false
# ============================================================
cat > "$PROJECT_DIR/app/workers/hls_worker.py" << 'PYEOF_HLS'
# -*- coding: utf-8 -*-
"""
app/workers/hls_worker.py
=========================
Воркер захвата одного потока камеры.

ИСПРАВЛЕНО (v27): если у камеры audio=false, в команду FFmpeg
добавляется флаг -an (без аудио).
"""
import asyncio
import logging
import re
import subprocess
import time
from pathlib import Path

from app.config import config
from app.services.camera_service import camera_service
from app.utils.ffmpeg import (
    build_ffmpeg_cmd,
    check_host,
    decide_stream_mode,
    probe_camera,
)

logger = logging.getLogger(__name__)

_STATS_RE = re.compile(
    r"frame=\s*(\d+)\s*fps=\s*([\d.]+)\s*q=\s*([\d.-]+)\s*"
    r"size=\s*([\d.]+[a-zA-Z]+)\s*time=(\S+)\s*bitrate=([\d.]+[a-zA-Z/]+)"
)


async def hls_worker(url: str, route_id: str, cam_id: str, manager) -> None:
    """Воркер захвата одного потока."""
    cfg = config.all()
    hls_cache = cfg.get("paths", {}).get("hls_cache", "hls_cache")
    ff_cfg = cfg.get("ffmpeg", {})
    global_cfg = ff_cfg.get("global", {})
    app_cfg = cfg.get("app", {})

    backoff = 1
    backoff_max = app_cfg.get("backoff_max", 30)

    # Создаём директорию для сегментов.
    project_root = Path(__file__).parent.parent.parent
    out_dir = project_root / hls_cache / "camera" / route_id
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error("❌ Не удалось создать директорию %s: %s", out_dir, e)
        return

    logger.info("🔍 Воркер запущен: %s", route_id)
    try:
        while True:
            cam = camera_service.get_camera(cam_id)
            if not cam or not cam.enabled:
                logger.info("⏹ Камера отключена, воркер завершается: %s", route_id)
                break

            manager.set_status(route_id, "подключение", "Подключение...")

            probe_timeout = global_cfg.get("probe_timeout", 3)
            if not await check_host(url, timeout=probe_timeout):
                manager.set_status(route_id, "недоступна", "Хост недоступен")
                logger.warning("⚠️ Хост недоступен: %s", route_id)
                await asyncio.sleep(min(backoff * 2, 15))
                backoff = min(backoff * 2, 15)
                continue

            backoff = 1
            manager.clear_log(route_id)

            try:
                loop = asyncio.get_running_loop()
                codec, profile, pix_fmt = await loop.run_in_executor(
                    None, probe_camera, url, global_cfg
                )
            except Exception:
                codec, profile, pix_fmt = "unknown", "unknown", "unknown"

            mode_cfg = ff_cfg.get("mode", "auto")
            if mode_cfg == "copy":
                mode = "copy"
            elif mode_cfg == "transcode":
                mode = "transcode"
            else:
                mode = decide_stream_mode(codec, profile, pix_fmt)
            logger.info("✅ %s: режим=%s (кодек=%s)", route_id, mode, codec)

            while True:
                cam = camera_service.get_camera(cam_id)
                if not cam or not cam.enabled:
                    break
                manager.set_status(route_id, "подключение", "Запуск потока...")

                cmd = build_ffmpeg_cmd(url, route_id, mode, ff_cfg, str(project_root / hls_cache))

                # НОВОЕ (v27): если у камеры audio=false, добавляем флаг -an.
                if not cam.audio:
                    # Вставляем -an перед выходным форматом (-f hls).
                    # Удаляем аудио-параметры, которые могли быть добавлены.
                    filtered = []
                    skip_next = False
                    for i, arg in enumerate(cmd):
                        if skip_next:
                            skip_next = False
                            continue
                        if arg in ("-c:a", "-b:a", "-ar", "-ac"):
                            skip_next = True
                            continue
                        filtered.append(arg)
                    # Добавляем -an перед -f hls
                    try:
                        f_index = filtered.index("-f")
                        filtered.insert(f_index, "-an")
                    except ValueError:
                        filtered.append("-an")
                    cmd = filtered
                    logger.info("🔇 %s: аудио отключено", route_id)

                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                    )

                    async def _read_logs():
                        buf = b""
                        try:
                            async for chunk in proc.stderr:
                                buf += chunk
                                while b"\n" in buf or b"\r" in buf:
                                    sep = b"\r" if b"\r" in buf else b"\n"
                                    line, buf = buf.split(sep, 1)
                                    if not line.strip():
                                        continue
                                    text = line.decode("utf-8", "ignore").strip()
                                    manager.add_log(
                                        route_id,
                                        f"[{time.strftime('%H:%M:%S')}] {text}",
                                    )
                                    m = _STATS_RE.search(text)
                                    if m:
                                        manager.set_status(
                                            route_id, "в_сети", "Поток активен",
                                            metrics={
                                                "fps": m.group(2),
                                                "bitrate": m.group(6),
                                                "time": m.group(5),
                                            },
                                        )
                        except Exception:
                            pass

                    log_task = asyncio.create_task(_read_logs())
                    return_code = await proc.wait()
                    log_task.cancel()
                    success = (return_code == 0)
                except Exception as e:
                    success = False
                    return_code = -1
                    logger.error("Ошибка конвертера для %s: %s", route_id, e)

                if success:
                    manager.set_status(route_id, "в_сети", "Поток активен")
                    backoff = 1
                else:
                    manager.set_status(route_id, "недоступна", f"Ошибка: {return_code}")
                    backoff = min(backoff * 2, backoff_max)
                    logger.warning(
                        "⚠️ Поток завершился с ошибкой %s для %s, повтор через %s с",
                        return_code, route_id, backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue
                break
    except asyncio.CancelledError:
        logger.info("⏹ Воркер отменён: %s", route_id)
    finally:
        manager.cleanup(route_id)
        logger.info("🧹 Воркер завершён: %s", route_id)
PYEOF_HLS
echo "  ✔ app/workers/hls_worker.py (поддержка audio=false)"

# ============================================================
# 3. app/services/camera_service.py — методы для audio/location
# ============================================================
cat > "$PROJECT_DIR/app/services/camera_service.py" << 'PYEOF_CAM'
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
PYEOF_CAM
echo "  ✔ app/services/camera_service.py (методы update_audio, update_location)"

# ============================================================
# 4. app/routes/api.py — эндпоинты для audio и location
# ============================================================
cat > "$PROJECT_DIR/app/routes/api.py" << 'PYEOF_API'
# -*- coding: utf-8 -*-
"""
app/routes/api.py
=================
Роуты ``/api/*``.

ИСПРАВЛЕНО (v27): добавлены эндпоинты /api/cameras/audio и
/api/cameras/location.
"""
import logging
from flask import jsonify, request

from app.config import config
from app.models import Event
from app.services.camera_service import camera_service
from app.services.stream_manager import stream_manager
from app.services.config_sync import config_sync

logger = logging.getLogger(__name__)


def _collect_system_stats() -> dict:
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu": round(cpu_percent, 1),
            "ram": round(memory.percent, 1),
            "ram_used_gb": round(memory.used / (1024 ** 3), 2),
            "ram_total_gb": round(memory.total / (1024 ** 3), 2),
            "disk": round(disk.percent, 1),
            "disk_used_gb": round(disk.used / (1024 ** 3), 2),
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        }
    except ImportError:
        return {
            "cpu": 0, "ram": 0, "ram_used_gb": 0, "ram_total_gb": 0,
            "disk": 0, "disk_used_gb": 0, "disk_total_gb": 0,
        }


def _collect_camera_stats() -> tuple:
    cameras = camera_service.all_cameras()
    stats = stream_manager.get_all_stats()
    total_cameras = len(cameras)
    enabled_cameras = sum(1 for c in cameras if c.enabled)
    online_streams = offline_streams = connecting_streams = 0
    camera_details = []
    for cam in cameras:
        route_id = cam.main_route_id
        status = stats.get(route_id, {})
        state = status.get("state", "подключение")
        if state == "в_сети":
            online_streams += 1
        elif state == "недоступна":
            offline_streams += 1
        else:
            connecting_streams += 1
        camera_details.append({
            "id": cam.id, "name": cam.name, "enabled": cam.enabled,
            "state": state, "msg": status.get("msg", ""),
            "metrics": status.get("metrics", {}),
        })
    summary = {
        "total_cameras": total_cameras,
        "enabled_cameras": enabled_cameras,
        "disabled_cameras": total_cameras - enabled_cameras,
        "online_streams": online_streams,
        "offline_streams": offline_streams,
        "connecting_streams": connecting_streams,
    }
    return summary, camera_details


def register(app):

    # Камеры
    @app.route("/api/cameras", methods=["GET"])
    def get_cameras():
        cameras = camera_service.all_cameras()
        return jsonify([c.to_dict() for c in cameras])

    @app.route("/api/cameras/save", methods=["POST"])
    def save_cameras():
        data = request.get_json()
        if not data or "cameras" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        saved = camera_service.save_cameras(data["cameras"])
        config_sync.sync_cameras(camera_service.all_cameras())
        return jsonify({"success": True, "saved": saved})

    @app.route("/api/cameras/toggle", methods=["POST"])
    def toggle_camera():
        data = request.get_json()
        if not data or "cam_id" not in data or "enabled" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        cam = camera_service.toggle_camera(data["cam_id"], data["enabled"])
        if not cam:
            return jsonify({"success": False, "msg": "Камера не найдена"}), 404
        return jsonify({"success": True, "camera": cam.to_dict()})

    @app.route("/api/cameras/comment", methods=["POST"])
    def update_comment():
        data = request.get_json()
        if not data or "cam_id" not in data or "comment" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        cam = camera_service.update_comment(data["cam_id"], data["comment"])
        if not cam:
            return jsonify({"success": False, "msg": "Камера не найдена"}), 404
        return jsonify({"success": True, "camera": cam.to_dict()})

    # НОВОЕ (v27): обновление флага audio
    @app.route("/api/cameras/audio", methods=["POST"])
    def update_audio():
        data = request.get_json()
        if not data or "cam_id" not in data or "audio" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        cam = camera_service.update_audio(data["cam_id"], data["audio"])
        if not cam:
            return jsonify({"success": False, "msg": "Камера не найдена"}), 404
        return jsonify({"success": True, "camera": cam.to_dict()})

    # НОВОЕ (v27): обновление местоположения
    @app.route("/api/cameras/location", methods=["POST"])
    def update_location():
        data = request.get_json()
        if not data or "cam_id" not in data or "location" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        cam = camera_service.update_location(data["cam_id"], data["location"])
        if not cam:
            return jsonify({"success": False, "msg": "Камера не найдена"}), 404
        return jsonify({"success": True, "camera": cam.to_dict()})

    # Наборы
    @app.route("/api/sets", methods=["GET"])
    def get_sets():
        sets = camera_service.all_sets()
        return jsonify({
            "default_set": camera_service.default_set_id(),
            "sets": {s_id: s.to_dict() for s_id, s in sets.items()},
        })

    @app.route("/api/sets/current", methods=["GET"])
    def get_current_set():
        current = camera_service.get_set(camera_service.current_set_id())
        if not current:
            return jsonify({
                "set_id": "", "set_name": "", "max_columns": 0,
                "max_rows": 0, "aspect_ratio": "16:9", "cameras": [],
            })
        cameras = camera_service.current_set_cameras()
        return jsonify({
            "set_id": current.id, "set_name": current.name,
            "max_columns": current.max_columns, "max_rows": current.max_rows,
            "aspect_ratio": current.aspect_ratio,
            "cameras": [c.to_dict() for c in cameras],
        })

    @app.route("/api/sets/save", methods=["POST"])
    def save_sets():
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        ok = camera_service.save_sets(data)
        if not ok:
            return jsonify({"success": False, "msg": "Неверный формат"}), 400
        return jsonify({"success": True})

    @app.route("/api/sets/switch", methods=["POST"])
    def switch_set():
        data = request.get_json()
        if not data or "set_id" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        ok = camera_service.switch_set(data["set_id"])
        if not ok:
            return jsonify({"success": False, "msg": "Набор не найден"}), 404
        return jsonify({"success": True})

    # Конфигурация
    @app.route("/api/config", methods=["GET"])
    def get_config():
        return jsonify(config.all())

    @app.route("/api/config/save", methods=["POST"])
    def save_config():
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        config.update(data)
        config.save()
        return jsonify({"success": True})

    # События
    @app.route("/api/events", methods=["GET"])
    def get_events():
        return jsonify([])

    @app.route("/api/events/publish", methods=["POST"])
    def publish_event():
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        event = Event.make(
            source=data.get("source", "system"),
            event_type=data.get("event_type", "unknown"),
            severity=data.get("severity", "info"),
            camera_id=data.get("camera_id"),
            payload=data.get("payload", {}),
        )
        config_sync.publish_event(event)
        return jsonify({"success": True, "event": event.to_dict()})

    # Дашборд
    @app.route("/api/dashboard", methods=["GET"])
    def dashboard():
        system = _collect_system_stats()
        stats_summary, camera_details = _collect_camera_stats()
        return jsonify({
            "system": system,
            "stats": stats_summary,
            "cameras": camera_details,
        })
PYEOF_API
echo "  ✔ app/routes/api.py (эндпоинты /api/cameras/audio и /location)"

# ============================================================
# 5. frontend/src/api.js — клиентские функции
# ============================================================
cat > "$PROJECT_DIR/frontend/src/api.js" << 'JSEOF'
// ============================================================
//  GRYPHONE — клиент API
//  ИСПРАВЛЕНО (v27): добавлены updateAudio и updateLocation.
// ============================================================
const API_BASE = '/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`Ошибка запроса: ${response.status}`)
  }
  return response.json()
}

export function getCameras() { return request('/cameras') }
export function saveCameras(cameras) {
  return request('/cameras/save', { method: 'POST', body: JSON.stringify({ cameras }) })
}
export function toggleCamera(camId, enabled) {
  return request('/cameras/toggle', { method: 'POST', body: JSON.stringify({ cam_id: camId, enabled }) })
}
export function updateComment(camId, comment) {
  return request('/cameras/comment', { method: 'POST', body: JSON.stringify({ cam_id: camId, comment }) })
}
// НОВОЕ (v27):
export function updateAudio(camId, audio) {
  return request('/cameras/audio', { method: 'POST', body: JSON.stringify({ cam_id: camId, audio }) })
}
export function updateLocation(camId, location) {
  return request('/cameras/location', { method: 'POST', body: JSON.stringify({ cam_id: camId, location }) })
}

export function getSets() { return request('/sets') }
export function getCurrentSetCameras() { return request('/sets/current') }
export function saveSets(data) {
  return request('/sets/save', { method: 'POST', body: JSON.stringify(data) })
}
export function switchSet(setId) {
  return request('/sets/switch', { method: 'POST', body: JSON.stringify({ set_id: setId }) })
}

export function getConfig() { return request('/config') }
export function saveConfig(data) {
  return request('/config/save', { method: 'POST', body: JSON.stringify(data) })
}
export function getEvents() { return request('/events') }
export function publishEvent(event) {
  return request('/events/publish', { method: 'POST', body: JSON.stringify(event) })
}
export function getDashboard() { return request('/dashboard') }
export function getFfmpegLogs() { return request('/ffmpeg_logs') }
JSEOF
echo "  ✔ frontend/src/api.js (добавлены updateAudio, updateLocation)"

# ============================================================
# 6. CameraCard.jsx — отображение location и иконки аудио
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/CameraCard.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — карточка камеры
//  ИСПРАВЛЕНО (v27): отображение location и иконки аудио.
// ============================================================
import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'

export default function CameraCard({ camera, status, aspectRatio, onContextMenu, onFullscreen }) {
  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  const [streamType, setStreamType] = useState('основной')
  const [error, setError] = useState(null)

  const routeId = `${camera.id}_${streamType}`
  const streamUrl = `/hls/camera/${routeId}/index.m3u8`
  const shouldPlay = camera.enabled && status !== 'недоступна'

  useEffect(() => {
    if (!shouldPlay || !videoRef.current) return
    setError(null)

    if (Hls.isSupported()) {
      const hls = new Hls()
      hls.loadSource(streamUrl)
      hls.attachMedia(videoRef.current)
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        videoRef.current.play().catch(() => {})
      })
      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          setError('Поток недоступен')
          hls.destroy()
          hlsRef.current = null
        }
      })
      hlsRef.current = hls
    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      videoRef.current.src = streamUrl
      videoRef.current.play().catch(() => setError('Не удалось воспроизвести'))
    }
    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
    }
  }, [streamUrl, shouldPlay])

  const handleDoubleClick = () => {
    if (onFullscreen) onFullscreen(camera)
  }

  const getStatusBadge = () => {
    if (!camera.enabled) return { text: 'Отключена', cls: 'status-offline' }
    if (status === 'в_сети') return { text: 'Онлайн', cls: 'status-online' }
    if (status === 'недоступна') return { text: 'Недоступна', cls: 'status-offline' }
    return { text: 'Подключение', cls: 'status-connecting' }
  }

  const badge = getStatusBadge()
  const aspectStyle = aspectRatio === '4:3' ? '75%' : '56.25%'

  return (
    <div
      className="camera-card"
      onContextMenu={(e) => {
        e.preventDefault()
        if (onContextMenu) onContextMenu(camera, e.clientX, e.clientY)
      }}
      onDoubleClick={handleDoubleClick}
      style={{ cursor: 'pointer' }}
      title="Двойной клик — на весь экран"
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="camera-name">{camera.name}</span>
        <span className={`status-badge ${badge.cls}`}>{badge.text}</span>
      </div>

      {/* НОВОЕ (v27): местоположение под именем */}
      {camera.location && (
        <div style={{
          fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }} title={camera.location}>
          📍 {camera.location}
        </div>
      )}

      <div style={{
        position: 'relative', width: '100%',
        paddingTop: aspectStyle, marginTop: '8px',
        background: '#0b0d10', borderRadius: '4px', overflow: 'hidden',
      }}>
        {camera.enabled && (
          <video
            ref={videoRef}
            muted
            playsInline
            style={{
              position: 'absolute', top: 0, left: 0,
              width: '100%', height: '100%', objectFit: 'contain',
            }}
          />
        )}

        {/* НОВОЕ (v27): иконка аудио в правом нижнем углу видео */}
        {camera.enabled && status === 'в_сети' && (
          <div style={{
            position: 'absolute', bottom: '4px', right: '4px',
            background: 'rgba(0, 0, 0, 0.6)', borderRadius: '4px',
            padding: '2px 6px', fontSize: '0.75rem',
          }}>
            {camera.audio ? '🔊' : '🔇'}
          </div>
        )}

        {error && (
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#dc2626', fontSize: '0.875rem', textAlign: 'center',
          }}>{error}</div>
        )}

        {!camera.enabled && (
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#94a3b8', fontSize: '0.875rem', textAlign: 'center',
          }}>Камера отключена</div>
        )}
      </div>

      {status === 'в_сети' && (
        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '4px' }}>
          {streamType === 'основной' ? 'Основной поток' : 'Дополнительный поток'}
        </div>
      )}
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/components/CameraCard.jsx (location + иконка аудио)"

# ============================================================
# 7. ContextMenu.jsx — редактирование location и toggle audio
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/ContextMenu.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — контекстное меню
//  ИСПРАВЛЕНО (v27): поля для location и toggle audio.
// ============================================================
import { useState, useEffect, useRef } from 'react'
import { toggleCamera, updateComment, updateAudio, updateLocation } from '../api'

export default function ContextMenu({ camera, x, y, onClose, onUpdate, onFullscreen }) {
  const [comment, setComment] = useState(camera.comment || '')
  const [location, setLocation] = useState(camera.location || '')
  const [audio, setAudio] = useState(camera.audio !== false)
  const menuRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  const menuWidth = 260
  const menuHeight = 520
  const adjustedX = Math.min(x, window.innerWidth - menuWidth)
  const adjustedY = Math.min(y, window.innerHeight - menuHeight)

  const handleToggle = async () => {
    try {
      await toggleCamera(camera.id, !camera.enabled)
      if (onUpdate) onUpdate()
      onClose()
    } catch (e) {
      console.error('Ошибка переключения камеры:', e)
    }
  }

  const handleSaveComment = async () => {
    try {
      await updateComment(camera.id, comment)
      if (onUpdate) onUpdate()
      onClose()
    } catch (e) {
      console.error('Ошибка сохранения комментария:', e)
    }
  }

  const handleFullscreen = () => {
    if (onFullscreen) onFullscreen(camera)
    onClose()
  }

  // НОВОЕ (v27): переключение аудио (с немедленным применением)
  const handleToggleAudio = async () => {
    const newAudio = !audio
    setAudio(newAudio)
    try {
      await updateAudio(camera.id, newAudio)
      if (window.addToast) {
        window.addToast(
          newAudio ? `🔊 Аудио включено для ${camera.name}` : `🔇 Аудио выключено для ${camera.name}`,
          'info'
        )
      }
      if (onUpdate) onUpdate()
    } catch (e) {
      console.error('Ошибка переключения аудио:', e)
    }
  }

  // НОВОЕ (v27): сохранение location
  const handleSaveLocation = async () => {
    try {
      await updateLocation(camera.id, location)
      if (window.addToast) {
        window.addToast(`📍 Местоположение сохранено: ${camera.name}`, 'success')
      }
      if (onUpdate) onUpdate()
      onClose()
    } catch (e) {
      console.error('Ошибка сохранения местоположения:', e)
    }
  }

  return (
    <div
      ref={menuRef}
      className="context-menu"
      style={{ position: 'fixed', left: adjustedX, top: adjustedY, zIndex: 100 }}
    >
      <div style={{
        fontWeight: 'bold', marginBottom: '12px',
        paddingBottom: '8px', borderBottom: '1px solid #334155',
      }}>
        {camera.name}
      </div>

      <button className="btn btn-primary" onClick={handleFullscreen}>
        🖥 На весь экран
      </button>

      <button
        className={`btn ${camera.enabled ? 'btn-danger' : 'btn-primary'}`}
        onClick={handleToggle}
      >
        {camera.enabled ? 'Отключить' : 'Включить'}
      </button>

      {/* НОВОЕ (v27): переключение аудио */}
      <button
        className={`btn ${audio ? 'btn-primary' : ''}`}
        onClick={handleToggleAudio}
        style={{ background: audio ? '#2563eb' : '#475569' }}
      >
        {audio ? '🔊 Аудио: ВКЛ' : '🔇 Аудио: ВЫКЛ'}
      </button>

      {/* НОВОЕ (v27): поле местоположения */}
      <div style={{ marginTop: '8px', marginBottom: '4px', fontSize: '0.75rem', color: '#94a3b8' }}>
        📍 Местоположение:
      </div>
      <input
        type="text"
        value={location}
        onChange={(e) => setLocation(e.target.value)}
        placeholder="Например: Здание 1, этаж 2"
        style={{
          background: '#0b0d10', color: '#e0e3e8',
          border: '1px solid #334155', borderRadius: '4px',
          padding: '6px 8px', fontSize: '0.875rem',
          width: '100%', marginBottom: '4px',
        }}
      />
      <button className="btn btn-primary" onClick={handleSaveLocation}>
        Сохранить местоположение
      </button>

      <div style={{ marginTop: '8px', marginBottom: '4px', fontSize: '0.75rem', color: '#94a3b8' }}>
        💬 Комментарий:
      </div>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Комментарий..."
        rows={2}
        style={{ width: '100%' }}
      />
      <button className="btn btn-primary" onClick={handleSaveComment}>
        Сохранить комментарий
      </button>

      <button className="btn" onClick={onClose}>
        Закрыть
      </button>
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/components/ContextMenu.jsx (audio + location)"

# ============================================================
# 8. migrate_add_fields.py — миграция существующих камер
# ============================================================
cat > "$PROJECT_DIR/migrate_add_fields.py" << 'PYEOF_MIGRATE'
# -*- coding: utf-8 -*-
"""
migrate_add_fields.py — миграция БД для новых полей.

Добавляет поля audio и location в существующие камеры:
  - audio: true (включено по умолчанию)
  - location: "" (пустая строка)

Запуск:  python migrate_add_fields.py
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path("rtsp_viewer.db")


def main():
    if not DB_PATH.exists():
        print(f"❌ БД не найдена: {DB_PATH.absolute()}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Получаем текущие камеры
    cursor.execute("SELECT value FROM settings WHERE key = 'cameras'")
    row = cursor.fetchone()
    if not row:
        print("⚠️  В БД нет камер. Миграция не нужна.")
        conn.close()
        return

    cameras = json.loads(row[0])
    print(f"📂 Найдено камер: {len(cameras)}")

    # Добавляем новые поля, если их нет
    added_audio = 0
    added_location = 0
    for cam in cameras:
        if "audio" not in cam:
            cam["audio"] = True
            added_audio += 1
        if "location" not in cam:
            cam["location"] = ""
            added_location += 1

    # Сохраняем обратно
    cursor.execute(
        "UPDATE settings SET value = ? WHERE key = 'cameras'",
        (json.dumps(cameras, ensure_ascii=False),)
    )
    conn.commit()
    conn.close()

    print(f"✅ Добавлено поле 'audio' у {added_audio} камер")
    print(f"✅ Добавлено поле 'location' у {added_location} камер")
    print()
    print("📋 Дальше:")
    print("   python main.py — перезапустить бэкенд")


if __name__ == "__main__":
    main()
PYEOF_MIGRATE
echo "  ✔ migrate_add_fields.py (миграция БД)"

# ------------------------------------------------------------
# Проверка
# ------------------------------------------------------------
for f in app/models.py app/workers/hls_worker.py app/services/camera_service.py app/routes/api.py frontend/src/api.js frontend/src/components/CameraCard.jsx frontend/src/components/ContextMenu.jsx migrate_add_fields.py; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Новые поля camera (audio, location) добавлены"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что нового:"
echo "  • Поле audio (bool): включение/выключение звука"
echo "  • Поле location (str): описание местоположения"
echo "  • Флаг -an в FFmpeg, если audio=false"
echo "  • Иконка 🔊/🔇 в углу видео"
echo "  • Поле 📍 location под именем камеры"
echo "  • Контекстное меню: toggle audio + редактирование location"
echo "  • Миграция БД: migrate_add_fields.py"
echo ""
echo "🚀 Дальше:"
echo "  1. Остановите бэкенд (Ctrl+C)"
echo "  2. python migrate_add_fields.py"
echo "  3. bash build_frontend.sh"
echo "  4. python main.py"
echo "  5. Откройте: http://localhost:5000 (Ctrl+Shift+R)"