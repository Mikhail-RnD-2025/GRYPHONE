# -*- coding: utf-8 -*-
"""
app/routes/hls.py
=================
Роуты для отдачи HLS-сегментов.

ИСПРАВЛЕНО (v26): явные MIME-типы для .m3u8 и .ts,
проверка безопасности пути.
"""
import logging
from pathlib import Path
from flask import send_from_directory, abort, Response

from app.config import config

logger = logging.getLogger(__name__)


def register(app):
    @app.route("/hls/camera/<route_id>/<path:filename>")
    def serve_hls(route_id, filename):
        """Отдаёт HLS-сегменты с правильными MIME-типами."""
        hls_cache = config.get("paths", "hls_cache", default="hls_cache")
        project_root = Path(__file__).parent.parent.parent
        directory = project_root / hls_cache / "camera" / route_id

        # Проверка безопасности пути.
        file_path = (directory / filename).resolve()
        if not str(file_path).startswith(str(directory.resolve())):
            logger.warning("⚠️ Попытка доступа за пределы каталога: %s", filename)
            abort(403)

        if not file_path.is_file():
            abort(404)

        # MIME-типы для HLS.
        ext = file_path.suffix.lower()
        if ext == ".m3u8":
            mime = "application/vnd.apple.mpegurl"
        elif ext == ".ts":
            mime = "video/mp2t"
        else:
            mime = "application/octet-stream"

        response = send_from_directory(str(directory), filename, mimetype=mime)
        # Заголовки для HLS: запрет кэширования плейлиста.
        if ext == ".m3u8":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
