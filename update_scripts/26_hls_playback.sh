#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 26: ИСПРАВЛЕНИЕ ВОСПРОИЗВЕДЕНИЯ HLS
#  ------------------------------------------------------------
#  Исправляет три проблемы, из-за которых видео не воспроизводится:
#    1. MIME-типы для .m3u8 и .ts
#    2. Перекодирование аудио pcm_mulaw → AAC
#    3. Убран флаг temp_file из hls_flags
#
#  Запуск:   bash update_scripts/26_hls_playback.sh
#  После:    python main.py (перезапуск)
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. app/__init__.py — MIME-типы для HLS (.m3u8 и .ts)
# ============================================================
cat > "$PROJECT_DIR/app/__init__.py" << 'PYEOF_FACTORY'
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
PYEOF_FACTORY
echo "  ✔ app/__init__.py (MIME-типы для .m3u8 и .ts)"

# ============================================================
# 2. app/routes/hls.py — явные MIME-типы при отдаче сегментов
# ============================================================
cat > "$PROJECT_DIR/app/routes/hls.py" << 'PYEOF_HLS'
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
PYEOF_HLS
echo "  ✔ app/routes/hls.py (явные MIME-типы + заголовки no-cache)"

# ============================================================
# 3. app/utils/ffmpeg.py — перекодирование аудио в AAC + убран temp_file
# ============================================================
cat > "$PROJECT_DIR/app/utils/ffmpeg.py" << 'PYEOF_FF'
# -*- coding: utf-8 -*-
"""
app/utils/ffmpeg.py
===================
ИСПРАВЛЕНО (v26):
  - Аудио перекодируется в AAC (вместо copy pcm_mulaw)
  - Убран флаг temp_file из hls_flags
  - Все пути — абсолютные
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
    if getattr(sys, "frozen", False):
        name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        path = Path(getattr(sys, "_MEIPASS", os.path.abspath("."))) / name
        if path.exists():
            return str(path)
    return shutil.which("ffmpeg")


def ffprobe_path():
    found = shutil.which("ffprobe")
    if not found:
        found = ffmpeg_path()
    return found


async def check_host(url: str, timeout: float = 2.0) -> bool:
    match = re.search(r"@([^:/]+)(?::(\d+))?", url)
    if not match:
        match = re.search(r"//([^:/]+)(?::(\d+))?", url)
    if not match:
        return False
    host = match.group(1)
    port = int(match.group(2)) if match.group(2) else 554
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout,
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return False


def probe_camera(url: str, global_cfg: dict):
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
    if codec == "h264" and "yuv420p" in pix_fmt:
        return "copy"
    return "transcode"


def detect_gpu_encoder():
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
    """Собирает команду FFmpeg.

    ИСПРАВЛЕНО (v26):
      - Аудио всегда перекодируется в AAC (для совместимости с HLS.js)
      - Убран флаг temp_file из hls_flags
      - Абсолютные пути
    """
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

    # Видео: copy или transcode.
    if mode == "copy":
        cmd += ["-c:v", "copy"]
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
        ]

    # ИСПРАВЛЕНО: Аудио ВСЕГДА перекодируется в AAC.
    # Браузеры (HLS.js) не умеют воспроизводить pcm_mulaw (G.711),
    # который встречается во многих IP-камерах.
    cmd += [
        "-c:a", "aac",
        "-b:a", transcode_cfg.get("audio_bitrate", "64k"),
        "-ar", "44100",
        "-ac", "2",
    ]

    # HLS-параметры.
    out_dir = Path(hls_cache) / "camera" / route_id

    # ИСПРАВЛЕНО: убран temp_file из hls_flags, чтобы сегменты сразу
    # записывались с финальными именами (.ts, а не .tmp).
    hls_flags = global_cfg.get(
        "hls_flags", "delete_segments+program_date_time"
    )
    # Принудительно убираем temp_file, если он там есть.
    hls_flags = "+".join(f for f in hls_flags.split("+") if f != "temp_file")

    cmd += [
        "-f", "hls",
        "-hls_time", str(global_cfg.get("hls_time", 2)),
        "-hls_list_size", str(global_cfg.get("hls_list_size", 4)),
        "-hls_flags", hls_flags,
        "-hls_segment_filename", str(out_dir / "seg_%03d.ts"),
        str(out_dir / "index.m3u8"),
    ]
    return cmd
PYEOF_FF
echo "  ✔ app/utils/ffmpeg.py (AAC-аудио, убран temp_file)"

# ============================================================
# 4. Очистка старых .tmp файлов из кэша (если остались)
# ============================================================
CACHE_DIR="$PROJECT_DIR/hls_cache"
if [ -d "$CACHE_DIR" ]; then
  echo "🧹 Очищаю старые .tmp файлы из $CACHE_DIR..."
  find "$CACHE_DIR" -name "*.tmp" -type f -delete 2>/dev/null || true
  find "$CACHE_DIR" -name "*.m3u8" -type f -delete 2>/dev/null || true
  find "$CACHE_DIR" -name "*.ts" -type f -delete 2>/dev/null || true
  echo "  ✔ Кэш очищен (старые сегменты удалены)"
fi

# ------------------------------------------------------------
# Проверка
# ------------------------------------------------------------
for f in app/__init__.py app/routes/hls.py app/utils/ffmpeg.py; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Исправление воспроизведения HLS применено"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что изменилось:"
echo "  • MIME-типы: .m3u8 → application/vnd.apple.mpegurl"
echo "  • MIME-типы: .ts → video/mp2t"
echo "  • Аудио: pcm_mulaw → AAC (поддерживается HLS.js)"
echo "  • Убран флаг temp_file из hls_flags"
echo "  • Плейлисты отдаются с Cache-Control: no-cache"
echo "  • Очищен старый кэш сегментов"
echo ""
echo "🚀 Дальше:"
echo "  1. Остановите бэкенд (Ctrl+C)"
echo "  2. Запустите: python main.py"
echo "  3. В браузере: Ctrl+Shift+R (жёсткая перезагрузка)"
echo "  4. Подождите 5-10 секунд — видео должно появиться"