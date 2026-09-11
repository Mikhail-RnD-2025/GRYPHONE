# -*- coding: utf-8 -*-
"""
app/routes/api.py
=================
Роуты ``/api/*``.

ИСПРАВЛЕНО (v27): добавлены эндпоинты /api/cameras/audio и
/api/cameras/location.
"""
import logging
from flask import jsonify, request, send_file

from app.config import config
from app.models import Event
from app.services.camera_service import camera_service
from app.services.camera_import_service import camera_import_service  # PATCH-191
from app.services.stream_manager import stream_manager
from app.services.config_sync import config_sync
from pathlib import Path  # PATCH-195

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
            "current_set": camera_service.current_set_id(),  # PATCH-182
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

    # PATCH-137: REST API для управления наборами

    @app.route("/api/sets", methods=["POST"])
    def create_set():
        """Создать новый набор"""
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name is required"}), 400
        set_id = (data.get("set_id") or name).strip()
        if set_id in camera_service._sets:
            return jsonify({"error": "Set ID already exists"}), 400
        sets_dict = {s: x.to_dict() for s, x in camera_service.all_sets().items()}
        # PATCH-144: валидация числовых полей (400 вместо 500)
        try:
            max_rows = min(max(int(data.get("max_rows", 1)), 1), 32)  # PATCH-145
            max_columns = min(max(int(data.get("max_columns", 1)), 1), 32)
        except (TypeError, ValueError):
            return jsonify({"error": "max_rows/max_columns must be integers"}), 400
        # PATCH-146: валидация aspect_ratio (16:9 или 4:3)
        aspect_ratio = data.get("aspect_ratio", "16:9")
        if aspect_ratio not in ("16:9", "4:3"):
            return jsonify({"error": "aspect_ratio must be '16:9' or '4:3'"}), 400
        sets_dict[set_id] = {
            "name": name,
            "max_rows": max_rows,
            "max_columns": max_columns,
            "aspect_ratio": aspect_ratio,
            "camera_ids": [],
        }
        camera_service.save_sets({"sets": sets_dict})
        return jsonify({"ok": True, "set": camera_service.get_set(set_id).to_dict()})

    @app.route("/api/sets/<set_id>", methods=["PUT"])
    def update_set(set_id):
        """Обновить набор (имя, размерность, камеры)"""
        target_set = camera_service.get_set(set_id)
        if not target_set:
            return jsonify({"error": "Set not found"}), 404
        data = request.get_json() or {}
        if "name" in data:
            target_set.name = data["name"]
        # PATCH-144: валидация числовых полей (400 вместо 500)
        try:
            if "max_rows" in data:
                target_set.max_rows = min(max(int(data["max_rows"]), 1), 32)
            if "max_columns" in data:
                target_set.max_columns = min(max(int(data["max_columns"]), 1), 32)
        except (TypeError, ValueError):
            return jsonify({"error": "max_rows/max_columns must be integers"}), 400
        # PATCH-146: валидация aspect_ratio
        if "aspect_ratio" in data:
            if data["aspect_ratio"] not in ("16:9", "4:3"):
                return jsonify({"error": "aspect_ratio must be '16:9' or '4:3'"}), 400
            target_set.aspect_ratio = data["aspect_ratio"]
        if "camera_ids" in data:
            target_set.camera_ids = [str(c) for c in data["camera_ids"]]
        sets_dict = {s: x.to_dict() for s, x in camera_service.all_sets().items()}
        camera_service.save_sets({"sets": sets_dict})
        return jsonify({"ok": True, "set": target_set.to_dict()})

    @app.route("/api/sets/<set_id>", methods=["DELETE"])
    def delete_set(set_id):
        """Удалить набор"""
        if set_id not in camera_service._sets:
            return jsonify({"error": "Set not found"}), 404
        if len(camera_service._sets) <= 1:
            return jsonify({"error": "Cannot delete the last set"}), 400
        sets_dict = {s: x.to_dict() for s, x in camera_service.all_sets().items()
                     if s != set_id}
        camera_service.save_sets({"sets": sets_dict})
        if getattr(camera_service, "_current_set", None) == set_id:
            if camera_service._sets:
                camera_service._current_set = next(iter(camera_service._sets))
        return jsonify({"ok": True})

    @app.route("/api/sets/<set_id>/cameras", methods=["POST"])
    def add_camera_to_set(set_id):
        """Добавить камеру в набор"""
        target_set = camera_service.get_set(set_id)
        if not target_set:
            return jsonify({"error": "Set not found"}), 404
        data = request.get_json() or {}
        camera_id = data.get("camera_id")
        if not camera_id:
            return jsonify({"error": "camera_id is required"}), 400
        if camera_id not in target_set.camera_ids:
            target_set.camera_ids.append(camera_id)
            sets_dict = {s: x.to_dict() for s, x in camera_service.all_sets().items()}
            camera_service.save_sets({"sets": sets_dict})
        return jsonify({"ok": True})

    @app.route("/api/sets/<set_id>/cameras/<camera_id>", methods=["DELETE"])
    def remove_camera_from_set(set_id, camera_id):
        """Убрать камеру из набора"""
        target_set = camera_service.get_set(set_id)
        if not target_set:
            return jsonify({"error": "Set not found"}), 404
        if camera_id in target_set.camera_ids:
            target_set.camera_ids.remove(camera_id)
            sets_dict = {s: x.to_dict() for s, x in camera_service.all_sets().items()}
            camera_service.save_sets({"sets": sets_dict})
        return jsonify({"ok": True})

    @app.route("/api/sets/<set_id>/cameras/order", methods=["PUT"])
    def update_cameras_order(set_id):
        """Изменить порядок камер в наборе"""
        target_set = camera_service.get_set(set_id)
        if not target_set:
            return jsonify({"error": "Set not found"}), 404
        data = request.get_json() or {}
        new_order = [str(c) for c in data.get("camera_ids", [])]
        if set(new_order) != set(target_set.camera_ids):
            return jsonify({"error": "Camera IDs mismatch"}), 400
        target_set.camera_ids = new_order
        sets_dict = {s: x.to_dict() for s, x in camera_service.all_sets().items()}
        camera_service.save_sets({"sets": sets_dict})
        return jsonify({"ok": True, "camera_ids": new_order})

    # ========================================================================
    # PATCH-192: экспорт/импорт камер (import-excel живёт в excel_import.py)
    # ========================================================================

    @app.route("/api/cameras/export-excel", methods=["GET"])
    def export_cameras_excel():
        """Экспорт камер в Excel-файл."""
        import tempfile
        import os
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp.close()
        try:
            result = camera_import_service.export_to_excel(Path(tmp.name))
            if not result.get("success"):
                return jsonify(result), 500
            return send_file(
                tmp.name,
                as_attachment=True,
                download_name="cameras.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        finally:
            import atexit
            atexit.register(lambda p=tmp.name: os.path.exists(p) and os.unlink(p))

    @app.route("/api/cameras/import-json", methods=["POST"])
    def import_cameras_json():
        """Импорт камер из JSON-массива."""
        data = request.get_json(silent=True)
        if data is None:
            # PATCH-193: fallback парсинг (для Windows CMD)
            try:
                import json as _json
                raw = request.get_data(as_text=True)
                data = _json.loads(raw)
            except Exception as e:
                logger.error(f"Не удалось распарсить JSON: {e}")
                return jsonify({"success": False, "error": f"Не удалось распарсить JSON: {e}"}), 400
        if not isinstance(data, list):
            return jsonify({"success": False, "error": "Ожидается JSON-массив камер"}), 400
        result = camera_import_service.import_from_json(data)
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result)


    @app.route("/api/cameras/export-json", methods=["GET"])
    def export_cameras_json():
        """Экспорт камер в JSON-массив."""
        return jsonify(camera_import_service.export_to_json())

    # ============================================================================
    # PATCH-208: Health Dashboard API
    # ============================================================================
    @app.route("/api/health/cameras")
    def health_cameras():
        """Статусы всех камер (main + sub) для dashboard."""
        import time as _time
        cameras = camera_service.all_cameras()
        all_stats = stream_manager.get_all_statuses()

        result = {}
        for cam in cameras:
            rid_main = f"{cam.id}_main"
            rid_sub = f"{cam.id}_sub"

            if not cam.enabled:
                st_main = {"state": "отключена", "msg": "Камера выключена", "metrics": {}}
                st_sub = {"state": "отключена", "msg": "Камера выключена", "metrics": {}}
            else:
                st_main = all_stats.get(rid_main, {"state": "не_запущен", "msg": "Воркер не запущен", "metrics": {}})
                st_sub = all_stats.get(rid_sub, {"state": "не_запущен", "msg": "Воркер не запущен", "metrics": {}})

            result[cam.id] = {
                "enabled": cam.enabled,
                "name": cam.name,
                "ip": cam.ipaddress,
                "main": st_main,
                "sub": st_sub,
            }

        enabled_cams = [c for c in result.values() if c["enabled"]]
        streaming = sum(1 for c in enabled_cams
                       if c["main"]["state"] == "в_сети" or c["sub"]["state"] == "в_сети")
        errors = sum(1 for c in enabled_cams
                    if c["main"]["state"] == "недоступна" or c["sub"]["state"] == "недоступна")
        connecting = sum(1 for c in enabled_cams
                        if c["main"]["state"] == "подключение" or c["sub"]["state"] == "подключение")

        return jsonify({
            "ts": _time.time(),
            "cameras": result,
            "summary": {
                "total": len(cameras),
                "enabled": len(enabled_cams),
                "disabled": len(cameras) - len(enabled_cams),
                "streaming": streaming,
                "connecting": connecting,
                "errors": errors,
            },
        })
    # ========================================================================
    # PATCH-218.3: SSE stream (декоратор + тело вместе, внутри register_routes)
    # ========================================================================
    @app.route("/api/health/cameras/stream")
    def health_stream():
        """SSE endpoint: пушит snapshot при подключении и при изменениях."""
        import queue as _q
        from flask import Response, stream_with_context

        def generate():
            q = stream_manager.subscribe()
            try:
                # initial snapshot
                all_stats = stream_manager.get_all_statuses()
                cameras = camera_service.all_cameras()
                initial = _build_health_payload(all_stats, cameras)
                yield f"data: {__import__('json').dumps(initial)}\n\n"

                while True:
                    try:
                        msg = q.get(timeout=15.0)
                        cameras_now = camera_service.all_cameras()
                        payload = _build_health_payload(msg["stats"], cameras_now)
                        yield f"data: {__import__('json').dumps(payload)}\n\n"
                    except _q.Empty:
                        yield ": keepalive\n\n"  # heartbeat
            except GeneratorExit:
                pass
            finally:
                stream_manager.unsubscribe(q)

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # ========================================================================
    # PATCH-227: GET /api/logs — читает хвост logs/gryphone.log
    # Формат ответа под LogsPage.jsx: {logs: [{timestamp, level, message}]}
    # ========================================================================
    @app.route("/api/logs")
    def get_logs():
        from flask import request, jsonify
        import re as _re
        log_path = Path(__file__).resolve().parent.parent.parent / "logs" / "gryphone.log"
        limit = min(int(request.args.get("limit", 500)), 2000)
        level_filter = request.args.get("level", "").upper()

        if not log_path.exists():
            return jsonify({"logs": []})

        # Читаем последние ~200KB (экономим память на больших логах)
        try:
            with log_path.open("rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 200 * 1024))
                tail = f.read().decode("utf-8", errors="replace")
        except Exception:
            return jsonify({"logs": []})

        # Формат: 2026-09-11 12:04:28,596 [INFO] app.services.stream_manager: текст
        hdr = _re.compile(
            r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[(\w+)\] ([^:]+): (.*)$"
        )
        entries = []
        for raw_line in tail.splitlines():
            m = hdr.match(raw_line)
            if m:
                entries.append({
                    "timestamp": m.group(1),
                    "level": m.group(2),
                    "logger": m.group(3),
                    "message": m.group(4),
                })
            elif entries:
                # продолжение предыдущей записи (traceback и т.п.)
                entries[-1]["message"] += "\n" + raw_line

        # Фильтр по уровню (если задан)
        if level_filter:
            entries = [e for e in entries if e["level"] == level_filter]

        # limit последних
        entries = entries[-limit:]

        # Формат под LogsPage: timestamp в ISO, level/message
        logs = []
        for e in entries:
            # Преобразуем "2026-09-11 12:04:28,596" → "2026-09-11T12:04:28.596"
            ts_iso = e["timestamp"].replace(" ", "T").replace(",", ".")
            logs.append({
                "timestamp": ts_iso,
                "level": e["level"],
                "message": f"[{e['logger']}] {e['message']}",
            })
        return jsonify({"logs": logs})


def _build_health_payload(stats: dict, cameras) -> dict:
    """PATCH-218: собирает health-пейлоад из stats и списка камер."""
    import time as _time
    result = {}
    for cam in cameras:
        rid_main = f"{cam.id}_main"
        rid_sub = f"{cam.id}_sub"
        if not cam.enabled:
            st_main = {"state": "отключена", "msg": "Камера выключена", "metrics": {}}
            st_sub = {"state": "отключена", "msg": "Камера выключена", "metrics": {}}
        else:
            st_main = stats.get(rid_main, {"state": "не_запущен", "msg": "Воркер не запущен", "metrics": {}})
            st_sub = stats.get(rid_sub, {"state": "не_запущен", "msg": "Воркер не запущен", "metrics": {}})
        result[cam.id] = {
            "enabled": cam.enabled, "name": cam.name, "ip": cam.ipaddress,
            "main": st_main, "sub": st_sub,
        }
    enabled_cams = [c for c in result.values() if c["enabled"]]
    return {
        "ts": _time.time(),
        "cameras": result,
        "summary": {
            "total": len(cameras),
            "enabled": len(enabled_cams),
            "disabled": len(cameras) - len(enabled_cams),
            "streaming": sum(1 for c in enabled_cams
                            if c["main"]["state"] == "в_сети" or c["sub"]["state"] == "в_сети"),
            "connecting": sum(1 for c in enabled_cams
                             if c["main"]["state"] == "подключение" or c["sub"]["state"] == "подключение"),
            "errors": sum(1 for c in enabled_cams
                         if c["main"]["state"] == "недоступна" or c["sub"]["state"] == "недоступна"),
        },
    }
