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
