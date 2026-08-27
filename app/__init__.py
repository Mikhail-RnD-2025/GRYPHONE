# -*- coding: utf-8 -*-
import mimetypes

# MIME-типы для фронтенда и HLS-потоков
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/vnd.apple.mpegurl", ".m3u8")
mimetypes.add_type("video/mp2t", ".ts")

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
    project_root = Path(__file__).parent.parent
    frontend_dist = project_root / "frontend" / "dist"
    app = Flask(__name__, static_folder=None)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    _register_frontend(app, frontend_dist)
    register_routes(app)

    stream_manager.start()
    if not stream_manager.wait_ready(timeout=5.0):
        logger.warning("⚠️ Цикл событий не готов")
    stream_manager.sync(camera_service.enabled_cameras())

    cleanup_thread = threading.Thread(
        target=cleanup_worker, daemon=True, name="CleanupWorker"
    )
    cleanup_thread.start()

    logger.info("✅ Приложение создано и настроено")
    return app

def _register_frontend(app: Flask, dist_dir: Path) -> None:
    @app.route("/")
    def index():
        if not (dist_dir / "index.html").is_file():
            return "<h3>Фронтенд не собран</h3>", 503
        return send_from_directory(str(dist_dir), "index.html", mimetype="text/html")

    @app.route("/assets/<path:filename>")
    def assets(filename):
        assets_dir = dist_dir / "assets"
        if not assets_dir.is_dir():
            abort(404)

        ext = Path(filename).suffix.lower()
        mime_map = {
            ".js": "application/javascript",
            ".mjs": "application/javascript",
            ".css": "text/css",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".ico": "image/x-icon",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
            ".ttf": "font/ttf",
            ".map": "application/json",
        }
        mime = mime_map.get(ext, "application/octet-stream")
        return send_from_directory(str(assets_dir), filename, mimetype=mime)

    @app.route("/<path:filename>")
    def static_files(filename):
        file_path = dist_dir / filename
        if file_path.is_file():
            return send_from_directory(str(dist_dir), filename)
        index_path = dist_dir / "index.html"
        if not index_path.is_file():
            abort(404)
        return send_from_directory(str(dist_dir), "index.html", mimetype="text/html")
