#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 23: ИСПРАВЛЕНИЕ MIME-ТИПОВ
#  ------------------------------------------------------------
#  Исправляет серую страницу: Flask на Windows отдавал JS/CSS
#  файлы с MIME-типом "text/plain" вместо правильных типов.
#  Браузер блокировал такие скрипты, и React не монтировался.
#
#  Запуск:   bash 23_mime_fix.sh
#  После:    python main.py (перезапуск)
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

cat > "$PROJECT_DIR/app/__init__.py" << 'PYEOF_FACTORY'
# -*- coding: utf-8 -*-
"""
app/__init__.py
===============
Фабрика приложения.

ИСПРАВЛЕНО (v23): явная регистрация MIME-типов для .js и .css.
На Windows реестр может не содержать правильного сопоставления,
и Flask отдаёт JS/CSS как text/plain, из-за чего браузер
блокирует модульные скрипты (ESM) и страница остаётся серой.
"""
import logging
import mimetypes
import threading
from pathlib import Path
from flask import Flask, send_from_directory, abort

# ИСПРАВЛЕНО: явно регистрируем MIME-типы до создания Flask.
# Это решает проблему "text/plain" для JS и CSS на Windows.
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/json", ".map")

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

    stream_manager.start()
    if not stream_manager.wait_ready(timeout=5.0):
        logger.warning("⚠️ Цикл событий не готов через 5 секунд, продолжаем")
    stream_manager.sync(camera_service.enabled_cameras())

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
        return send_from_directory(
            str(dist_dir), "index.html", mimetype="text/html"
        )

    @app.route("/assets/<path:filename>")
    def assets(filename):
        """Отдаёт ассеты фронтенда с правильным MIME-типом."""
        assets_dir = dist_dir / "assets"
        if not assets_dir.is_dir():
            abort(404)

        # Определяем MIME-тип по расширению вручную (страховка).
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

        return send_from_directory(
            str(assets_dir), filename, mimetype=mime
        )

    @app.route("/<path:filename>")
    def static_files(filename):
        """Отдаёт статические файлы и фоллбэк для одностраничника."""
        file_path = dist_dir / filename
        if file_path.is_file():
            return send_from_directory(str(dist_dir), filename)
        index_path = dist_dir / "index.html"
        if not index_path.is_file():
            abort(404)
        return send_from_directory(
            str(dist_dir), "index.html", mimetype="text/html"
        )
PYEOF_FACTORY
echo "  ✔ app/__init__.py (явные MIME-типы для JS/CSS)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Исправление применено"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что изменилось:"
echo "  • Явно прописаны MIME-типы для .js, .css, .mjs, .svg"
echo "  • Роут /assets/<path> отдаёт файлы с правильным типом"
echo ""
echo "🚀 Дальше:"
echo "  1. Остановите бэкенд (Ctrl+C)"
echo "  2. Запустите снова: python main.py"
echo "  3. В браузере: Ctrl+Shift+R (жёсткая перезагрузка)"
echo "  4. Откройте: http://localhost:5000"