#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 08: HTTP-РОУТЫ
#  ------------------------------------------------------------
#  Заполняет:
#    - app/routes/__init__.py — регистрация роутов
#    - app/routes/api.py      — /api/* (камеры, наборы, конфиг, события)
#    - app/routes/stream.py   — /api/stream_status (события в реальном
#                               времени) и /api/ffmpeg_logs
#    - app/routes/hls.py      — /hls/... (отдача сегментов)
#
#  Запуск:   bash 08_backend_routes.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# app/routes/__init__.py — регистрация роутов
# ============================================================
cat > "$PROJECT_DIR/app/routes/__init__.py" << 'PYEOF_INIT'
# -*- coding: utf-8 -*-
"""
Пакет HTTP-роутов приложения.

Модули:
  - api    : роуты /api/* (камеры, наборы, конфиг, события)
  - stream : роуты /api/stream_status и /api/ffmpeg_logs
  - hls    : роуты /hls/* (отдача сегментов)
"""
from app.routes import api, stream, hls


def register_routes(app):
    """Регистрирует все роуты в приложении."""
    api.register(app)
    stream.register(app)
    hls.register(app)
PYEOF_INIT
echo "  ✔ app/routes/__init__.py"

# ============================================================
# app/routes/api.py — /api/*
# ============================================================
cat > "$PROJECT_DIR/app/routes/api.py" << 'PYEOF_API'
# -*- coding: utf-8 -*-
"""
app/routes/api.py
=================
Роуты ``/api/*``: управление камерами, наборами, конфигурацией.

Использует сервисы из ``app.services`` для бизнес-логики.
"""
import logging
from flask import jsonify, request

from app.config import config
from app.models import Event
from app.services.camera_service import camera_service
from app.services.config_sync import config_sync

logger = logging.getLogger(__name__)


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
        # Синхронизируем с внешними системами (каркас, пока не активен).
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
        """Сохраняет конфигурацию из запроса."""
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        # Здесь можно добавить валидацию и слияние.
        # Пока просто сохраняем как есть.
        config.save()
        return jsonify({"success": True})

    # ------------------------------------------------------------------
    # События (своя база событий)
    # ------------------------------------------------------------------
    @app.route("/api/events", methods=["GET"])
    def get_events():
        """Возвращает список событий (пока заглушка).

        .. todo:: Реализовать чтение из таблицы событий в БД.
        """
        # TODO: Реализовать чтение событий из БД.
        return jsonify([])

    @app.route("/api/events/publish", methods=["POST"])
    def publish_event():
        """Публикует событие (пока заглушка).

        .. todo:: Реализовать запись события в БД и отправку в шину.
        """
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        # Создаём объект события (пока не сохраняем).
        event = Event.make(
            source=data.get("source", "system"),
            event_type=data.get("event_type", "unknown"),
            severity=data.get("severity", "info"),
            camera_id=data.get("camera_id"),
            payload=data.get("payload", {}),
        )
        # Отправляем во внешние системы (каркас, пока не активен).
        config_sync.publish_event(event)
        return jsonify({"success": True, "event": event.to_dict()})

    # ------------------------------------------------------------------
    # Дашборд
    # ------------------------------------------------------------------
    @app.route("/api/dashboard", methods=["GET"])
    def dashboard():
        """Возвращает данные для дашборда (пока заглушка).

        .. todo:: Реализовать сбор статистики (загрузка системы, камеры).
        """
        # TODO: Реализовать сбор статистики.
        return jsonify({
            "system": {"cpu": 0, "ram": 0, "disk": 0},
            "stats": {"total": 0, "online": 0, "offline": 0, "error": 0},
            "cameras": [],
        })
PYEOF_API
echo "  ✔ app/routes/api.py"

# ============================================================
# app/routes/stream.py — события в реальном времени и логи
# ============================================================
cat > "$PROJECT_DIR/app/routes/stream.py" << 'PYEOF_STREAM'
# -*- coding: utf-8 -*-
"""
app/routes/stream.py
====================
Роуты для событий в реальном времени и логов потоков.

Использует менеджер стримера из ``app.services.stream_manager``.
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
        """Отдаёт статусы потоков в реальном времени (события в реальном времени).

        Возвращает поток данных в формате событий, который браузер
        читает через объект ``EventSource``.
        """
        def generate():
            while True:
                stats = stream_manager.get_all_stats()
                yield f"data: {json.dumps(stats)}\n\n"
                time.sleep(config.get("производительность", "интервал_событий", default=1.0))

        return Response(generate(), mimetype="text/event-stream")

    @app.route("/api/ffmpeg_logs")
    def ffmpeg_logs():
        """Возвращает логи потоков (последние строки)."""
        logs = stream_manager.get_logs(limit=100)
        return jsonify(logs)
PYEOF_STREAM
echo "  ✔ app/routes/stream.py"

# ============================================================
# app/routes/hls.py — /hls/*
# ============================================================
cat > "$PROJECT_DIR/app/routes/hls.py" << 'PYEOF_HLS'
# -*- coding: utf-8 -*-
"""
app/routes/hls.py
=================
Роуты для отдачи сегментов потоков.

Отдаёт файлы из каталога кэша сегментов. Путь к кэшу берётся из
конфигурации (секция "пути").
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
        """Отдаёт файл сегмента или плейлист для потока."""
        hls_cache = config.get("пути", "кэш_hls", default="hls_cache")
        directory = Path(hls_cache) / "камера" / route_id
        # Проверяем, что файл существует.
        file_path = directory / filename
        if not file_path.is_file():
            abort(404)
        return send_from_directory(str(directory), filename)
PYEOF_HLS
echo "  ✔ app/routes/hls.py"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in app/routes/__init__.py app/routes/api.py app/routes/stream.py app/routes/hls.py; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo "✅ HTTP-роуты готовы (с правильным синтаксисом)."
echo "ℹ️  Фабрика приложения и точка входа — скрипт 12."