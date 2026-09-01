#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 17: ИСПРАВЛЕНИЕ КРИТИЧЕСКИХ ОШИБОК
#  ------------------------------------------------------------
#  Исправляет все найденные ошибки:
#    1. app/utils/ffmpeg.py     — аргументы конвертера на английском,
#                                  правильные имена файлов
#    2. app/workers/hls_worker.py — правильные ключи конфига
#    3. app/workers/cleanup_worker.py — правильные ключи конфига
#    4. app/routes/stream.py    — правильные ключи конфига
#    5. app/routes/hls.py       — правильные ключи конфига + путь
#    6. frontend/src/pages/MonitorPage.jsx — правильный ключ статуса
#    7. app/__init__.py         — защита от гонки при старте
#
#  Запуск:   bash 17_fix_critical.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. app/utils/ffmpeg.py — ИСПРАВЛЕНО: аргументы конвертера
# ============================================================
cat > "$PROJECT_DIR/app/utils/ffmpeg.py" << 'PYEOF_FF'
# -*- coding: utf-8 -*-
"""
app/utils/ffmpeg.py
===================
Утилиты для работы с внешним конвертером видео.

ИСПРАВЛЕНО: все аргументы конвертера теперь на английском,
имена выходных файлов — английские (совпадают с фронтендом).
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


# ---------------------------------------------------------------------------
# Поиск бинарников
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# ИСПРАВЛЕННАЯ проверка доступности хоста
# ---------------------------------------------------------------------------
async def check_host(url: str, timeout: float = 2.0) -> bool:
    """Быстро проверяет, доступен ли хост камеры по ссылке.

    Аргументы:
      url     -- ссылка на поток камеры;
      timeout -- максимальное время ожидания соединения, секунды.

    Возвращает ``True``, если хост доступен, иначе ``False``.
    """
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


# ---------------------------------------------------------------------------
# Зондирование камеры
# ---------------------------------------------------------------------------
def probe_camera(url: str, global_cfg: dict):
    """Определяет параметры видео камеры с помощью пробника.

    Возвращает кортеж ``(кодек, профиль, формат_пикселей)``.
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
        "-timeout", str(timeout),
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


# ---------------------------------------------------------------------------
# Выбор режима обработки
# ---------------------------------------------------------------------------
def decide_stream_mode(codec: str, profile: str, pix_fmt: str) -> str:
    """Выбирает режим обработки потока."""
    if codec == "h264" and "yuv420p" in pix_fmt:
        return "copy"
    return "transcode"


# ---------------------------------------------------------------------------
# Определение кодировщика
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Сборка команды запуска конвертера
# ---------------------------------------------------------------------------
def build_ffmpeg_cmd(url: str, route_id: str, mode: str,
                     ffmpeg_cfg: dict, hls_cache: str) -> list:
    """Собирает команду запуска конвертера для генерации сегментов.

    ИСПРАВЛЕНО: все аргументы на английском, имена файлов английские.
    """
    global_cfg = ffmpeg_cfg.get("global", {})
    logging_cfg = ffmpeg_cfg.get("logging", {})
    transcode_cfg = ffmpeg_cfg.get("transcode", {})

    cmd = [ffmpeg_path() or "ffmpeg"]
    # Скрываем баннер.
    if logging_cfg.get("hide_banner", True):
        cmd.append("-hide_banner")
    # Уровень и период статистики.
    cmd += [
        "-loglevel", logging_cfg.get("level", "info"),
        "-stats_period", str(logging_cfg.get("stats_period", 1)),
    ]
    # Входные параметры.
    cmd += [
        "-rtsp_transport", global_cfg.get("transport", "tcp"),
        "-fflags", f"{global_cfg.get('buffer_mode', 'nobuffer')}+discardcorrupt",
        "-flags", "low_delay",
        "-err_detect", global_cfg.get("error_detection", "ignore_err"),
        "-threads", str(global_cfg.get("threads", 0)),
        "-i", url,
    ]

    # Параметры обработки в зависимости от режима.
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

    # Выходные параметры: генерация сегментов.
    # ИСПРАВЛЕНО: имена файлов английские, совпадают с фронтендом.
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
echo "  ✔ app/utils/ffmpeg.py (исправлено: аргументы и имена файлов)"

# ============================================================
# 2. app/workers/hls_worker.py — ИСПРАВЛЕНО: ключи конфига
# ============================================================
cat > "$PROJECT_DIR/app/workers/hls_worker.py" << 'PYEOF_HLS'
# -*- coding: utf-8 -*-
"""
app/workers/hls_worker.py
=========================
Воркер захвата одного потока камеры.

ИСПРАВЛЕНО: ключи конфигурации теперь английские.
"""
import asyncio
import logging
import re
import subprocess
import time

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
    # ИСПРАВЛЕНО: английские ключи конфига.
    hls_cache = cfg.get("paths", {}).get("hls_cache", "hls_cache")
    ff_cfg = cfg.get("ffmpeg", {})
    global_cfg = ff_cfg.get("global", {})
    app_cfg = cfg.get("app", {})

    backoff = 1
    backoff_max = app_cfg.get("backoff_max", 30)

    logger.info("🔍 Воркер запущен: %s", route_id)
    try:
        while True:
            cam = camera_service.get_camera(cam_id)
            if not cam or not cam.enabled:
                logger.info("⏹ Камера отключена, воркер завершается: %s", route_id)
                break

            manager.set_status(route_id, "подключение", "Подключение...")

            # ИСПРАВЛЕНО: английский ключ конфига.
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

            # ИСПРАВЛЕНО: английский ключ конфига.
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

                cmd = build_ffmpeg_cmd(url, route_id, mode, ff_cfg, hls_cache)
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
echo "  ✔ app/workers/hls_worker.py (исправлено: ключи конфига)"

# ============================================================
# 3. app/workers/cleanup_worker.py — ИСПРАВЛЕНО: ключи конфига
# ============================================================
cat > "$PROJECT_DIR/app/workers/cleanup_worker.py" << 'PYEOF_CLEAN'
# -*- coding: utf-8 -*-
"""
app/workers/cleanup_worker.py
=============================
Фоновая задача очистки кэша сегментов.

ИСПРАВЛЕНО: ключи конфигурации теперь английские.
"""
import logging
import time
from pathlib import Path

from app.config import config

logger = logging.getLogger(__name__)


def cleanup_worker() -> None:
    """Бесконечный цикл очистки кэша сегментов."""
    while True:
        try:
            cfg = config.all()
            # ИСПРАВЛЕНО: английский ключ конфига.
            clean_cfg = cfg.get("cleanup", {})
            if not clean_cfg.get("enabled", True):
                time.sleep(60)
                continue

            # ИСПРАВЛЕНО: английский ключ конфига.
            hls_cache = cfg.get("paths", {}).get("hls_cache", "hls_cache")
            cache_dir = Path(hls_cache)
            if not cache_dir.is_dir():
                time.sleep(300)
                continue

            now = time.time()
            # ИСПРАВЛЕНО: английский ключ конфига.
            max_age_sec = clean_cfg.get("max_age_hours", 24) * 3600

            for cam_dir in cache_dir.iterdir():
                if not cam_dir.is_dir():
                    continue
                for stream_dir in cam_dir.iterdir():
                    if not stream_dir.is_dir():
                        continue
                    for f in stream_dir.iterdir():
                        if f.suffix == ".ts" and (now - f.stat().st_mtime) > max_age_sec:
                            try:
                                f.unlink()
                            except OSError:
                                pass
                    try:
                        if not any(stream_dir.iterdir()):
                            stream_dir.rmdir()
                    except OSError:
                        pass
        except Exception as e:
            logger.warning("Ошибка очистки кэша: %s", e)

        # ИСПРАВЛЕНО: английский ключ конфига.
        interval = config.get("cleanup", "interval_seconds", default=300)
        time.sleep(interval)
PYEOF_CLEAN
echo "  ✔ app/workers/cleanup_worker.py (исправлено: ключи конфига)"

# ============================================================
# 4. app/routes/stream.py — ИСПРАВЛЕНО: ключи конфига
# ============================================================
cat > "$PROJECT_DIR/app/routes/stream.py" << 'PYEOF_STREAM'
# -*- coding: utf-8 -*-
"""
app/routes/stream.py
====================
Роуты для событий в реальном времени и логов потоков.

ИСПРАВЛЕНО: ключи конфигурации теперь английские.
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
        """Отдаёт статусы потоков в реальном времени."""
        def generate():
            while True:
                stats = stream_manager.get_all_stats()
                yield f"data: {json.dumps(stats)}\n\n"
                # ИСПРАВЛЕНО: английский ключ конфига.
                time.sleep(config.get("performance", "sse_interval", default=1.0))

        return Response(generate(), mimetype="text/event-stream")

    @app.route("/api/ffmpeg_logs")
    def ffmpeg_logs():
        """Возвращает логи потоков."""
        logs = stream_manager.get_logs(limit=100)
        return jsonify(logs)
PYEOF_STREAM
echo "  ✔ app/routes/stream.py (исправлено: ключи конфига)"

# ============================================================
# 5. app/routes/hls.py — ИСПРАВЛЕНО: ключи конфига + путь
# ============================================================
cat > "$PROJECT_DIR/app/routes/hls.py" << 'PYEOF_HLS'
# -*- coding: utf-8 -*-
"""
app/routes/hls.py
=================
Роуты для отдачи сегментов потоков.

ИСПРАВЛЕНО: ключи конфигурации английские, путь к каталогу "camera".
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
        # ИСПРАВЛЕНО: английский ключ конфига.
        hls_cache = config.get("paths", "hls_cache", default="hls_cache")
        # ИСПРАВЛЕНО: имя каталога "camera" (совпадает с воркером).
        directory = Path(hls_cache) / "camera" / route_id
        file_path = directory / filename
        if not file_path.is_file():
            abort(404)
        return send_from_directory(str(directory), filename)
PYEOF_HLS
echo "  ✔ app/routes/hls.py (исправлено: ключи конфига + путь)"

# ============================================================
# 6. frontend/src/pages/MonitorPage.jsx — ИСПРАВЛЕНО: ключ статуса
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница мониторинга
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО: статусы читаются по ключу {camera.id}_main,
//  так как статусы хранятся по идентификатору потока (route_id).
// ============================================================
import { useState, useEffect } from 'react'
import Header from '../components/Header'
import CameraCard from '../components/CameraCard'
import ContextMenu from '../components/ContextMenu'
import Toasts from '../components/Toasts'
import useStreamStatus from '../hooks/useStreamStatus'
import { getCameras } from '../api'

export default function MonitorPage() {
  const [cameras, setCameras] = useState([])
  const [contextMenu, setContextMenu] = useState(null)

  const stats = useStreamStatus()

  useEffect(() => {
    loadCameras()
  }, [])

  const loadCameras = async () => {
    try {
      const data = await getCameras()
      setCameras(data)
    } catch (e) {
      console.error('Ошибка загрузки камер:', e)
    }
  }

  const handleContextMenu = (camera, x, y) => {
    setContextMenu({ camera, x, y })
  }

  const handleCloseContextMenu = () => {
    setContextMenu(null)
  }

  return (
    <div className="page">
      <Header />

      <div className="camera-grid">
        {cameras.map((camera) => {
          // ИСПРАВЛЕНО: статус хранится по ключу {camera.id}_main.
          const routeId = camera.id + '_main'
          const status = stats[routeId]?.state || 'подключение'
          return (
            <CameraCard
              key={camera.id}
              camera={camera}
              status={status}
              onContextMenu={handleContextMenu}
            />
          )
        })}
      </div>

      {contextMenu && (
        <ContextMenu
          camera={contextMenu.camera}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={handleCloseContextMenu}
          onUpdate={loadCameras}
        />
      )}

      <Toasts />
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/MonitorPage.jsx (исправлено: ключ статуса)"

# ============================================================
# 7. app/__init__.py — ИСПРАВЛЕНО: защита от гонки при старте
# ============================================================
cat > "$PROJECT_DIR/app/__init__.py" << 'PYEOF_FACTORY'
# -*- coding: utf-8 -*-
"""
app/__init__.py
===============
Фабрика приложения: создаёт Flask, регистрирует API-роуты, раздаёт
собранный фронтенд, запускает стример и воркеры.

ИСПРАВЛЕНО: добавлена задержка после старта цикла, чтобы избежать
гонки при вызове синхронизации воркеров.
"""
import logging
import threading
import time
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

    # ИСПРАВЛЕНО: небольшая задержка, чтобы цикл событий успел стартовать.
    time.sleep(0.1)

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
    """Регистрирует раздачу собранного фронтенда + SPA-фоллбэк."""

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
        """Отдаёт статические файлы и SPA-фоллбэк."""
        file_path = dist_dir / filename
        if file_path.is_file():
            return send_from_directory(str(dist_dir), filename)
        index_path = dist_dir / "index.html"
        if not index_path.is_file():
            abort(404)
        return send_from_directory(str(dist_dir), "index.html")
PYEOF_FACTORY
echo "  ✔ app/__init__.py (исправлено: защита от гонки)"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in app/utils/ffmpeg.py app/workers/hls_worker.py app/workers/cleanup_worker.py app/routes/stream.py app/routes/hls.py frontend/src/pages/MonitorPage.jsx app/__init__.py; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Все критические ошибки исправлены"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что исправлено:"
echo "  1. Аргументы конвертера — на английском"
echo "  2. Имена файлов (плейлист, сегменты) — английские"
echo "  3. Ключи конфигурации — английские (совпадают с settings.json)"
echo "  4. Путь к каталогу кэша — 'camera' (совпадает с воркером)"
echo "  5. Ключ статуса на фронтенде — {camera.id}_main"
echo "  6. Защита от гонки при старте стримера"
echo ""
echo "🚀 Запустите:  python main.py"
echo "   В логах появятся строки запуска воркеров и конвертера."