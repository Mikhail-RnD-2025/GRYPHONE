#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 22: ИСПРАВЛЕНИЕ ОШИБОК БЭКЕНДА И API
#  ------------------------------------------------------------
#  Исправляет:
#    1. app/config.py              — добавлен метод update()
#    2. app/routes/api.py          — сохранение конфига обновляет данные
#    3. app/utils/ffmpeg.py        — замена -timeout на -rw_timeout
#    4. app/routes/stream.py       — заголовки для потока событий
#    5. app/routes/hls.py          — проверка безопасности пути
#    6. frontend/src/components/CameraCard.jsx — streamType = main/sub
#    7. app/services/stream_manager.py — метод wait_ready()
#    8. app/__init__.py            — защита от гонки через событие
#
#  Запуск:   bash 22_backend_fixes.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. app/config.py — добавлен метод update()
# ============================================================
cat > "$PROJECT_DIR/app/config.py" << 'PYEOF_CONFIG'
# -*- coding: utf-8 -*-
"""
app/config.py
=============
Управление конфигурацией приложения.

ДОБАВЛЕНО: метод update() для изменения конфигурации извне (например,
через API). Это исправляет ошибку, при которой сохранение конфига
не обновляло данные.
"""
import copy
import logging
from typing import Any, Dict

from app.database import db

logger = logging.getLogger(__name__)


def default_config() -> Dict[str, Any]:
    """Возвращает конфигурацию по умолчанию."""
    return {
        "server": {"host": "0.0.0.0", "port": 5000},
        "paths": {
            "cameras_db": "rtsp_viewer.db",
            "sets_db": "rtsp_viewer.db",
            "hls_cache": "hls_cache",
        },
        "ffmpeg": {
            "mode": "auto",
            "logging": {"level": "info", "stats_period": 1,
                        "hide_banner": True, "generate_report": False},
            "global": {
                "transport": "tcp", "buffer_mode": "nobuffer",
                "error_detection": "ignore_err", "threads": 0,
                "probe_timeout": 3, "probe_analyze_duration": 1000000,
                "probe_size": 1000000, "hls_time": 2, "hls_list_size": 4,
                "hls_flags": "delete_segments+temp_file+program_date_time",
            },
            "copy": {"note": "Прямой поток"},
            "transcode": {
                "gpu_encoder": "auto", "video_bitrate": "2500k",
                "video_maxrate": "4000k", "video_bufsize": "8000k",
                "gop_size": 30, "keyint_min": 30, "audio_bitrate": "48k",
                "pix_fmt": "yuv420p", "preset": "ultrafast", "tune": "zerolatency",
            },
        },
        "app": {
            "backoff_max": 30, "stable_runtime_threshold": 60,
            "gpu_fallback_threshold": 5.0, "cleanup_min_file_size": 512,
            "default_set": "",
        },
        "cleanup": {"enabled": True, "interval_seconds": 300, "max_age_hours": 24},
        "performance": {"probe_workers": 32, "sse_interval": 1.0},
        "events": {"enabled": True, "retention_days": 30, "db_path": "rtsp_viewer.db"},
        "storage": {"default": "", "targets": []},
        "integration": {"enabled": False},
        "analytics": {"enabled": False},
        "cluster": {"enabled": False},
    }


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Рекурсивно сливает ``override`` в ``base``."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class ConfigManager:
    """Доступ к конфигурации приложения."""

    KEY = "config"

    def __init__(self):
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """Загружает сохранённую конфигурацию и сливает с дефолтной."""
        saved = db.get(self.KEY, {}) or {}
        return _deep_merge(default_config(), saved)

    def reload(self) -> None:
        """Перечитывает конфигурацию из БД."""
        self._data = self._load()

    def save(self) -> None:
        """Сохраняет текущую конфигурацию в БД."""
        db.save(self.KEY, self._data)

    # ДОБАВЛЕНО: метод для обновления конфигурации извне.
    def update(self, new_data: Dict[str, Any]) -> None:
        """Обновляет конфигурацию из словаря (слияние с текущей).

        Используется в API для сохранения изменений конфигурации.
        """
        self._data = _deep_merge(self._data, new_data)

    def all(self) -> Dict[str, Any]:
        """Возвращает полную конфигурацию (копию)."""
        return copy.deepcopy(self._data)

    def get(self, *path: str, default: Any = None) -> Any:
        """Возвращает параметр по пути."""
        node: Any = self._data
        for key in path:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return copy.deepcopy(node)

    def section(self, name: str) -> Dict[str, Any]:
        """Возвращает целую секцию конфигурации (копию)."""
        value = self._data.get(name, {})
        return copy.deepcopy(value) if isinstance(value, dict) else {}


config = ConfigManager()
PYEOF_CONFIG
echo "  ✔ app/config.py (добавлен метод update)"

# ============================================================
# 2. app/routes/api.py — исправлено сохранение конфига
# ============================================================
cat > "$PROJECT_DIR/app/routes/api.py" << 'PYEOF_API'
# -*- coding: utf-8 -*-
"""
app/routes/api.py
=================
Роуты ``/api/*``: управление камерами, наборами, конфигурацией, дашборд.

ИСПРАВЛЕНО: роут /api/config/save теперь обновляет конфигурацию
из запроса перед сохранением (ранее сохранял старый конфиг).
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
    """Собирает статистику системных ресурсов."""
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
        logger.warning("⚠️ Модуль мониторинга не установлен")
        return {
            "cpu": 0, "ram": 0, "ram_used_gb": 0, "ram_total_gb": 0,
            "disk": 0, "disk_used_gb": 0, "disk_total_gb": 0,
        }


def _collect_camera_stats() -> tuple:
    """Собирает статистику по камерам и потокам."""
    cameras = camera_service.all_cameras()
    stats = stream_manager.get_all_stats()

    total_cameras = len(cameras)
    enabled_cameras = sum(1 for c in cameras if c.enabled)
    online_streams = 0
    offline_streams = 0
    connecting_streams = 0
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
            "id": cam.id,
            "name": cam.name,
            "enabled": cam.enabled,
            "state": state,
            "msg": status.get("msg", ""),
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
    """Регистрирует роуты ``/api/*`` в приложении."""

    # ------------------------------------------------------------------
    # Камеры
    # ------------------------------------------------------------------
    @app.route("/api/cameras", methods=["GET"])
    def get_cameras():
        """Возвращает список всех камер."""
        cameras = camera_service.all_cameras()
        return jsonify([c.to_dict() for c in cameras])

    @app.route("/api/cameras/save", methods=["POST"])
    def save_cameras():
        """Сохраняет список камер из запроса."""
        data = request.get_json()
        if not data or "cameras" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        saved = camera_service.save_cameras(data["cameras"])
        config_sync.sync_cameras(camera_service.all_cameras())
        return jsonify({"success": True, "saved": saved})

    @app.route("/api/cameras/toggle", methods=["POST"])
    def toggle_camera():
        """Включает/выключает камеру."""
        data = request.get_json()
        if not data or "cam_id" not in data or "enabled" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        cam = camera_service.toggle_camera(data["cam_id"], data["enabled"])
        if not cam:
            return jsonify({"success": False, "msg": "Камера не найдена"}), 404
        return jsonify({"success": True, "camera": cam.to_dict()})

    @app.route("/api/cameras/comment", methods=["POST"])
    def update_comment():
        """Обновляет комментарий камеры."""
        data = request.get_json()
        if not data or "cam_id" not in data or "comment" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        cam = camera_service.update_comment(data["cam_id"], data["comment"])
        if not cam:
            return jsonify({"success": False, "msg": "Камера не найдена"}), 404
        return jsonify({"success": True, "camera": cam.to_dict()})

    # ------------------------------------------------------------------
    # Наборы
    # ------------------------------------------------------------------
    @app.route("/api/sets", methods=["GET"])
    def get_sets():
        """Возвращает все наборы камер."""
        sets = camera_service.all_sets()
        return jsonify({
            "default_set": camera_service.default_set_id(),
            "sets": {s_id: s.to_dict() for s_id, s in sets.items()},
        })

    @app.route("/api/sets/current", methods=["GET"])
    def get_current_set():
        """Возвращает камеры активного набора и информацию о наборе."""
        current = camera_service.get_set(camera_service.current_set_id())

        if not current:
            return jsonify({
                "set_id": "",
                "set_name": "",
                "max_columns": 0,
                "max_rows": 0,
                "aspect_ratio": "16:9",
                "cameras": [],
            })

        cameras = camera_service.current_set_cameras()
        return jsonify({
            "set_id": current.id,
            "set_name": current.name,
            "max_columns": current.max_columns,
            "max_rows": current.max_rows,
            "aspect_ratio": current.aspect_ratio,
            "cameras": [c.to_dict() for c in cameras],
        })

    @app.route("/api/sets/save", methods=["POST"])
    def save_sets():
        """Сохраняет наборы из запроса."""
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        ok = camera_service.save_sets(data)
        if not ok:
            return jsonify({"success": False, "msg": "Неверный формат"}), 400
        return jsonify({"success": True})

    @app.route("/api/sets/switch", methods=["POST"])
    def switch_set():
        """Переключает активный набор."""
        data = request.get_json()
        if not data or "set_id" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        ok = camera_service.switch_set(data["set_id"])
        if not ok:
            return jsonify({"success": False, "msg": "Набор не найден"}), 404
        return jsonify({"success": True})

    # ------------------------------------------------------------------
    # Конфигурация
    # ------------------------------------------------------------------
    @app.route("/api/config", methods=["GET"])
    def get_config():
        """Возвращает текущую конфигурацию."""
        return jsonify(config.all())

    @app.route("/api/config/save", methods=["POST"])
    def save_config():
        """Сохраняет конфигурацию из запроса.

        ИСПРАВЛЕНО: теперь обновляет конфигурацию из запроса перед
        сохранением (ранее сохранял старый конфиг).
        """
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        # ИСПРАВЛЕНО: обновляем конфиг из запроса.
        config.update(data)
        config.save()
        return jsonify({"success": True})

    # ------------------------------------------------------------------
    # События
    # ------------------------------------------------------------------
    @app.route("/api/events", methods=["GET"])
    def get_events():
        """Возвращает список событий."""
        return jsonify([])

    @app.route("/api/events/publish", methods=["POST"])
    def publish_event():
        """Публикует событие."""
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

    # ------------------------------------------------------------------
    # Дашборд
    # ------------------------------------------------------------------
    @app.route("/api/dashboard", methods=["GET"])
    def dashboard():
        """Возвращает данные для дашборда."""
        system = _collect_system_stats()
        stats_summary, camera_details = _collect_camera_stats()
        return jsonify({
            "system": system,
            "stats": stats_summary,
            "cameras": camera_details,
        })
PYEOF_API
echo "  ✔ app/routes/api.py (исправлено сохранение конфига)"

# ============================================================
# 3. app/utils/ffmpeg.py — замена -timeout на -rw_timeout
# ============================================================
cat > "$PROJECT_DIR/app/utils/ffmpeg.py" << 'PYEOF_FF'
# -*- coding: utf-8 -*-
"""
app/utils/ffmpeg.py
===================
Утилиты для работы с внешним конвертером видео.

ИСПРАВЛЕНО: аргумент -timeout заменён на -rw_timeout (стандартный
аргумент для таймаута чтения/записи в микросекундах).
"""
import asyncio
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def ffmpeg_path():
    """Возвращает путь к бинарнику конвертера или ``None``, если не найден."""
    if getattr(sys, "frozen", False):
        name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        path = Path(getattr(sys, "_MEIPASS", os.path.abspath("."))) / name
        if path.exists():
            return str(path)
    found = shutil.which("ffmpeg")
    return found


def ffprobe_path():
    """Возвращает путь к бинарнику пробника или ``None``, если не найден."""
    found = shutil.which("ffprobe")
    if not found:
        found = ffmpeg_path()
    return found


async def check_host(url: str, timeout: float = 2.0) -> bool:
    """Быстро проверяет, доступен ли хост камеры по ссылке."""
    match = re.search(r"@([^:/]+)(?::(\d+))?", url)
    if not match:
        match = re.search(r"//([^:/]+)(?::(\d+))?", url)
    if not match:
        logger.warning("⚠️ Не удалось извлечь хост из ссылки: %s", url)
        return False

    host = match.group(1)
    port = int(match.group(2)) if match.group(2) else 554

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return False


def probe_camera(url: str, global_cfg: dict):
    """Определяет параметры видео камеры с помощью пробника.

    ИСПРАВЛЕНО: -timeout заменён на -rw_timeout (в микросекундах).
    """
    binary = ffprobe_path()
    if not binary:
        return "unknown", "unknown", "unknown"

    timeout = global_cfg.get("probe_timeout", 3)
    analyze_duration = global_cfg.get("probe_analyze_duration", 1000000)
    probe_size = global_cfg.get("probe_size", 1000000)

    cmd = [
        binary,
        "-v", "error",
        "-show_entries", "stream=codec_name,profile,pix_fmt",
        "-of", "json",
        "-select_streams", "v:0",
        "-analyzeduration", str(analyze_duration),
        "-probesize", str(probe_size),
        # ИСПРАВЛЕНО: -rw_timeout вместо -timeout (в микросекундах).
        "-rw_timeout", str(int(timeout * 1000000)),
        url,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 2
        )
        if result.returncode == 0 and result.stdout:
            import json
            streams = json.loads(result.stdout).get("streams", [{}])
            if streams:
                first = streams[0]
                return (
                    first.get("codec_name", "unknown"),
                    first.get("profile", "unknown"),
                    first.get("pix_fmt", "unknown"),
                )
    except Exception:
        pass
    return "unknown", "unknown", "unknown"


def decide_stream_mode(codec: str, profile: str, pix_fmt: str) -> str:
    """Выбирает режим обработки потока."""
    if codec == "h264" and "yuv420p" in pix_fmt:
        return "copy"
    return "transcode"


def detect_gpu_encoder():
    """Определяет доступный аппаратный или программный кодировщик."""
    try:
        output = subprocess.check_output(
            [ffmpeg_path() or "ffmpeg", "-hide_banner", "-encoders"],
            stderr=subprocess.STDOUT, text=True, timeout=3,
        ).lower()
        if "h264_nvenc" in output:
            return "h264_nvenc", ["-preset", "p1", "-tune", "ll"]
        if "h264_qsv" in output:
            return "h264_qsv", ["-preset", "fast"]
        if "h264_amf" in output:
            return "h264_amf", ["-usage", "ultralowlatency"]
    except Exception:
        pass
    return "libx264", ["-preset", "ultrafast", "-tune", "zerolatency"]


def build_ffmpeg_cmd(url: str, route_id: str, mode: str,
                     ffmpeg_cfg: dict, hls_cache: str) -> list:
    """Собирает команду запуска конвертера для генерации сегментов."""
    global_cfg = ffmpeg_cfg.get("global", {})
    logging_cfg = ffmpeg_cfg.get("logging", {})
    transcode_cfg = ffmpeg_cfg.get("transcode", {})

    cmd = [ffmpeg_path() or "ffmpeg"]
    if logging_cfg.get("hide_banner", True):
        cmd.append("-hide_banner")
    cmd += [
        "-loglevel", logging_cfg.get("level", "info"),
        "-stats_period", str(logging_cfg.get("stats_period", 1)),
    ]
    cmd += [
        "-rtsp_transport", global_cfg.get("transport", "tcp"),
        "-fflags", f"{global_cfg.get('buffer_mode', 'nobuffer')}+discardcorrupt",
        "-flags", "low_delay",
        "-err_detect", global_cfg.get("error_detection", "ignore_err"),
        "-threads", str(global_cfg.get("threads", 0)),
        "-i", url,
    ]

    if mode == "copy":
        cmd += ["-c:v", "copy", "-c:a", "copy"]
    else:
        encoder = transcode_cfg.get("gpu_encoder", "auto")
        if encoder == "auto":
            encoder, _ = detect_gpu_encoder()
        cmd += ["-c:v", encoder]
        cmd += [
            "-b:v", transcode_cfg.get("video_bitrate", "2500k"),
            "-maxrate", transcode_cfg.get("video_maxrate", "4000k"),
            "-bufsize", transcode_cfg.get("video_bufsize", "8000k"),
            "-g", str(transcode_cfg.get("gop_size", 30)),
            "-keyint_min", str(transcode_cfg.get("keyint_min", 30)),
            "-pix_fmt", transcode_cfg.get("pix_fmt", "yuv420p"),
            "-c:a", "aac",
            "-b:a", transcode_cfg.get("audio_bitrate", "48k"),
        ]

    out_dir = Path(hls_cache) / "camera" / route_id
    cmd += [
        "-f", "hls",
        "-hls_time", str(global_cfg.get("hls_time", 2)),
        "-hls_list_size", str(global_cfg.get("hls_list_size", 4)),
        "-hls_flags", global_cfg.get(
            "hls_flags", "delete_segments+temp_file+program_date_time"
        ),
        "-hls_segment_filename", str(out_dir / "seg_%03d.ts"),
        str(out_dir / "index.m3u8"),
    ]
    return cmd
PYEOF_FF
echo "  ✔ app/utils/ffmpeg.py (замена -timeout на -rw_timeout)"

# ============================================================
# 4. app/routes/stream.py — заголовки для потока событий
# ============================================================
cat > "$PROJECT_DIR/app/routes/stream.py" << 'PYEOF_STREAM'
# -*- coding: utf-8 -*-
"""
app/routes/stream.py
====================
Роуты для событий в реальном времени и логов потоков.

ИСПРАВЛЕНО: добавлены заголовки для корректной работы потока событий
(запрет буферизации, поддержка постоянного соединения).
"""
import json
import logging
import time
from flask import Response, jsonify

from app.config import config
from app.services.stream_manager import stream_manager

logger = logging.getLogger(__name__)


def register(app):
    """Регистрирует роуты событий и логов в приложении."""

    @app.route("/api/stream_status")
    def stream_status():
        """Отдаёт статусы потоков в реальном времени.

        ИСПРАВЛЕНО: добавлены заголовки для корректной работы
        потока событий (запрет буферизации).
        """
        def generate():
            while True:
                stats = stream_manager.get_all_stats()
                yield f"data: {json.dumps(stats)}\n\n"
                time.sleep(config.get("performance", "sse_interval", default=1.0))

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                # ИСПРАВЛЕНО: заголовки для корректной работы потока событий.
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.route("/api/ffmpeg_logs")
    def ffmpeg_logs():
        """Возвращает логи потоков."""
        logs = stream_manager.get_logs(limit=100)
        return jsonify(logs)
PYEOF_STREAM
echo "  ✔ app/routes/stream.py (заголовки для потока событий)"

# ============================================================
# 5. app/routes/hls.py — проверка безопасности пути
# ============================================================
cat > "$PROJECT_DIR/app/routes/hls.py" << 'PYEOF_HLS'
# -*- coding: utf-8 -*-
"""
app/routes/hls.py
=================
Роуты для отдачи сегментов потоков.

ИСПРАВЛЕНО: добавлена проверка безопасности пути для предотвращения
выхода за пределы каталога (защита от атак через ../).
"""
import logging
from pathlib import Path
from flask import send_from_directory, abort

from app.config import config

logger = logging.getLogger(__name__)


def register(app):
    """Регистрирует роуты ``/hls/*`` в приложении."""

    @app.route("/hls/camera/<route_id>/<path:filename>")
    def serve_hls(route_id, filename):
        """Отдаёт файл сегмента или плейлист для потока.

        ИСПРАВЛЕНО: добавлена проверка безопасности пути.
        """
        hls_cache = config.get("paths", "hls_cache", default="hls_cache")
        directory = Path(hls_cache) / "camera" / route_id

        # ИСПРАВЛЕНО: проверка безопасности пути.
        # Разрешаем путь и проверяем, что он находится внутри целевого каталога.
        file_path = (directory / filename).resolve()
        if not str(file_path).startswith(str(directory.resolve())):
            logger.warning("⚠️ Попытка доступа за пределы каталога: %s", filename)
            abort(403)

        if not file_path.is_file():
            abort(404)
        return send_from_directory(str(directory), filename)
PYEOF_HLS
echo "  ✔ app/routes/hls.py (проверка безопасности пути)"

# ============================================================
# 6. frontend/src/components/CameraCard.jsx — streamType = main/sub
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/CameraCard.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — компонент «Карточка камеры»
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО: значения типов потока изменены с русских
//  («основной»/«дополнительный») на английские (основной/дополнительный),
//  чтобы совпадать с идентификаторами на бэкенде (_основной/_дополнительный).
// ============================================================
import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'

export default function CameraCard({ camera, status, aspectRatio, onContextMenu }) {
  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  // ИСПРАВЛЕНО: значения типов потока теперь английские.
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

  // Переключение между потоками по двойному клику.
  const handleDoubleClick = () => {
    if (camera.sub_url && camera.sub_url !== camera.main_url) {
      // ИСПРАВЛЕНО: переключаем между 'основной' и 'дополнительный'.
      setStreamType(prev => prev === 'основной' ? 'дополнительный' : 'основной')
    }
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
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="camera-name">{camera.name}</span>
        <span className={`status-badge ${badge.cls}`}>{badge.text}</span>
      </div>

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

        {error && (
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#dc2626', fontSize: '0.875rem', textAlign: 'center',
          }}>
            {error}
          </div>
        )}

        {!camera.enabled && (
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#94a3b8', fontSize: '0.875rem', textAlign: 'center',
          }}>
            Камера отключена
          </div>
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
echo "  ✔ frontend/src/components/CameraCard.jsx (типы потока исправлены)"

# ============================================================
# 7. app/services/stream_manager.py — добавлен метод wait_ready()
# ============================================================
cat > "$PROJECT_DIR/app/services/stream_manager.py" << 'PYEOF_SM'
# -*- coding: utf-8 -*-
"""
app/services/stream_manager.py
==============================
Сервис управления асинхронными воркерами захвата потоков и их статусами.

ДОБАВЛЕНО: метод wait_ready() для ожидания готовности цикла событий.
Это исправляет хрупкую защиту от гонки при старте (ранее использовался
time.sleep).
"""
import asyncio
import logging
import threading
from collections import deque
from typing import Dict, List, Optional

from app.models import Camera

logger = logging.getLogger(__name__)


class StreamManager:
    """Управление воркерами захвата и статусами потоков."""

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._tasks: Dict[str, asyncio.Task] = {}
        self._stats: Dict[str, dict] = {}
        self._logs: Dict[str, deque] = {}
        self._lock = threading.RLock()
        self._log_lock = threading.Lock()
        self._started = False
        # ДОБАВЛЕНО: событие для сигнализации готовности цикла.
        self._ready_event = threading.Event()

    def start(self) -> None:
        """Запускает асинхронный цикл событий в отдельном потоке."""
        if self._started:
            return
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="StreamManagerLoop"
        )
        self._thread.start()
        self._started = True
        logger.info("⚡ Асинхронный цикл стримера запущен")

    def _run_loop(self) -> None:
        """Точка входа для потока с циклом событий."""
        asyncio.set_event_loop(self._loop)
        # ДОБАВЛЕНО: сигнализируем, что цикл готов.
        self._loop.call_soon(self._ready_event.set)
        self._loop.run_forever()

    # ДОБАВЛЕНО: метод для ожидания готовности цикла событий.
    def wait_ready(self, timeout: float = 5.0) -> bool:
        """Ждёт готовности цикла событий.

        Возвращает ``True``, если цикл готов, ``False`` — если таймаут.
        """
        return self._ready_event.wait(timeout)

    def stop(self) -> None:
        """Останавливает все воркеры и цикл событий."""
        if not self._started or self._loop is None:
            return
        for task in list(self._tasks.values()):
            self._loop.call_soon_threadsafe(task.cancel)
        self._tasks.clear()
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._started = False
        logger.info("⏹ Асинхронный цикл стримера остановлен")

    def sync(self, cameras: List[Camera]) -> None:
        """Синхронизирует воркеры со списком камер."""
        if not self._started or self._loop is None:
            logger.warning("⚠️ Стример не запущен, синхронизация отложена")
            return
        asyncio.run_coroutine_threadsafe(self._sync(cameras), self._loop)

    async def _sync(self, cameras: List[Camera]) -> None:
        """Асинхронная синхронизация воркеров."""
        from app.workers.hls_worker import hls_worker

        needed: Dict[str, tuple] = {}
        for cam in cameras:
            if not cam.enabled:
                continue
            needed[cam.main_route_id] = (cam.main_url, cam.id)
            if cam.sub_url and cam.sub_url != cam.main_url:
                needed[cam.sub_route_id] = (cam.sub_url, cam.id)

        with self._lock:
            for rid in list(self._tasks.keys()):
                if rid not in needed:
                    task = self._tasks.pop(rid)
                    task.cancel()
                    self._stats.pop(rid, None)
                    logger.info("⏹ Остановлен воркер: %s", rid)
            for rid, (url, cam_id) in needed.items():
                if rid not in self._tasks:
                    task = self._loop.create_task(
                        hls_worker(url, rid, cam_id, self)
                    )
                    self._tasks[rid] = task
                    logger.info("🚀 Запущен воркер: %s", rid)

    def set_status(self, route_id: str, state: str, msg: str = "",
                   metrics: Optional[dict] = None) -> None:
        """Устанавливает статус потока."""
        with self._lock:
            self._stats[route_id] = {
                "state": state,
                "msg": msg,
                "metrics": metrics or {},
            }

    def get_all_stats(self) -> Dict[str, dict]:
        """Возвращает статусы всех потоков (копию словаря)."""
        with self._lock:
            return dict(self._stats)

    def get_status(self, route_id: str) -> Optional[dict]:
        """Возвращает статус одного потока или ``None``."""
        with self._lock:
            return self._stats.get(route_id)

    def add_log(self, route_id: str, line: str, maxlen: int = 500) -> None:
        """Добавляет строку в лог потока."""
        with self._log_lock:
            if route_id not in self._logs:
                self._logs[route_id] = deque(maxlen=maxlen)
            self._logs[route_id].append(line)

    def clear_log(self, route_id: str) -> None:
        """Очищает лог потока."""
        with self._log_lock:
            if route_id in self._logs:
                self._logs[route_id].clear()

    def get_logs(self, limit: int = 100) -> Dict[str, List[str]]:
        """Возвращает последние строки логов всех потоков."""
        with self._log_lock:
            return {
                rid: list(d)[-limit:]
                for rid, d in self._logs.items()
            }

    def cleanup(self, route_id: str) -> None:
        """Удаляет задачу и статус потока."""
        with self._lock:
            self._tasks.pop(route_id, None)
            self._stats.pop(route_id, None)


stream_manager = StreamManager()
PYEOF_SM
echo "  ✔ app/services/stream_manager.py (добавлен метод wait_ready)"

# ============================================================
# 8. app/__init__.py — защита от гонки через событие
# ============================================================
cat > "$PROJECT_DIR/app/__init__.py" << 'PYEOF_FACTORY'
# -*- coding: utf-8 -*-
"""
app/__init__.py
===============
Фабрика приложения: создаёт веб-фреймворк, регистрирует роуты, раздаёт
собранный фронтенд и запускает фоновые задачи.

ИСПРАВЛЕНО: защита от гонки при старте теперь использует событие
готовности цикла (ранее использовался хрупкий time.sleep).
"""
import logging
import threading
from pathlib import Path
from flask import Flask, send_from_directory, abort

from app.config import config
from app.services.stream_manager import stream_manager
from app.services.camera_service import camera_service
from app.workers.cleanup_worker import cleanup_worker
from app.routes import register_routes

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Создаёт и настраивает приложение."""
    project_root = Path(__file__).parent.parent
    frontend_dist = project_root / "frontend" / "dist"

    app = Flask(__name__, static_folder=None)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    _register_frontend(app, frontend_dist)
    register_routes(app)

    # Запускаем менеджер стримера.
    stream_manager.start()

    # ИСПРАВЛЕНО: ждём готовности цикла через событие (не хрупкий time.sleep).
    if not stream_manager.wait_ready(timeout=5.0):
        logger.warning("⚠️ Цикл событий не готов через 5 секунд, продолжаем")

    # Запускаем воркеры для всех включённых камер.
    stream_manager.sync(camera_service.enabled_cameras())

    # Запускаем фоновую очистку кэша.
    cleanup_thread = threading.Thread(
        target=cleanup_worker, daemon=True, name="CleanupWorker"
    )
    cleanup_thread.start()

    logger.info("✅ Приложение создано и настроено")
    return app


def _register_frontend(app: Flask, dist_dir: Path) -> None:
    """Регистрирует раздачу собранного фронтенда + фоллбэк для одностраничника."""

    @app.route("/")
    def index():
        """Главная страница."""
        if not (dist_dir / "index.html").is_file():
            return (
                "<h3>Фронтенд не собран</h3>"
                "<p>Выполните: <code>bash build_frontend.sh</code></p>",
                503,
            )
        return send_from_directory(str(dist_dir), "index.html")

    @app.route("/assets/<path:filename>")
    def assets(filename):
        """Отдаёт ассеты фронтенда."""
        assets_dir = dist_dir / "assets"
        if not assets_dir.is_dir():
            abort(404)
        return send_from_directory(str(assets_dir), filename)

    @app.route("/<path:filename>")
    def static_files(filename):
        """Отдаёт статические файлы и фоллбэк для одностраничника."""
        file_path = dist_dir / filename
        if file_path.is_file():
            return send_from_directory(str(dist_dir), filename)
        index_path = dist_dir / "index.html"
        if not index_path.is_file():
            abort(404)
        return send_from_directory(str(dist_dir), "index.html")
PYEOF_FACTORY
echo "  ✔ app/__init__.py (защита от гонки через событие)"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in app/config.py app/routes/api.py app/utils/ffmpeg.py app/routes/stream.py app/routes/hls.py frontend/src/components/CameraCard.jsx app/services/stream_manager.py app/__init__.py; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Все ошибки бэкенда и API исправлены"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что исправлено:"
echo "  • app/config.py: добавлен метод update() для изменения конфига"
echo "  • app/routes/api.py: сохранение конфига обновляет данные из запроса"
echo "  • app/utils/ffmpeg.py: -timeout заменён на -rw_timeout"
echo "  • app/routes/stream.py: заголовки для потока событий"
echo "  • app/routes/hls.py: проверка безопасности пути"
echo "  • CameraCard.jsx: типы потока исправлены на английские"
echo "  • stream_manager.py: добавлен метод wait_ready()"
echo "  • app/__init__.py: защита от гонки через событие"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000"