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
