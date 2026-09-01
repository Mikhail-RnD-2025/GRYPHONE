#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 24: СОЗДАНИЕ ДИРЕКТОРИЙ ДЛЯ HLS-СЕГМЕНТОВ
#  ------------------------------------------------------------
#  Исправляет ошибку "Failed to open file ... No such file or
#  directory" при записи сегментов HLS. FFmpeg не создаёт
#  промежуточные директории автоматически, поэтому нужно явно
#  создавать их перед запуском.
#
#  Что делает:
#    - Обновляет app/workers/hls_worker.py
#    - Добавляет out_dir.mkdir(parents=True, exist_ok=True)
#      перед запуском FFmpeg
#
#  Запуск:   bash update_scripts/24_mkdir_fix.sh
#  После:    Остановить бэкенд (Ctrl+C) → python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

cat > "$PROJECT_DIR/app/workers/hls_worker.py" << 'PYEOF_HLS'
# -*- coding: utf-8 -*-
"""
app/workers/hls_worker.py
=========================
Воркер захвата одного потока камеры.

ИСПРАВЛЕНО (v24): автоматическое создание директории для
сегментов HLS перед запуском FFmpeg.
"""
import asyncio
import logging
import re
import subprocess
import time
from pathlib import Path

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
    hls_cache = cfg.get("paths", {}).get("hls_cache", "hls_cache")
    ff_cfg = cfg.get("ffmpeg", {})
    global_cfg = ff_cfg.get("global", {})
    app_cfg = cfg.get("app", {})

    backoff = 1
    backoff_max = app_cfg.get("backoff_max", 30)

    # ============================================================
    # ИСПРАВЛЕНО: создаём директорию для сегментов ДО запуска FFmpeg.
    # FFmpeg не создаёт промежуточные папки автоматически,
    # поэтому без этого шага запись seg_000.ts.tmp падает с ошибкой
    # "No such file or directory".
    # ============================================================
    project_root = Path(__file__).parent.parent.parent
    out_dir = project_root / hls_cache / "camera" / route_id
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        logger.info("📁 Создана директория: %s", out_dir)
    except OSError as e:
        logger.error("❌ Не удалось создать директорию %s: %s", out_dir, e)
        return

    logger.info("🔍 Воркер запущен: %s", route_id)
    try:
        while True:
            cam = camera_service.get_camera(cam_id)
            if not cam or not cam.enabled:
                logger.info("⏹ Камера отключена, воркер завершается: %s", route_id)
                break

            manager.set_status(route_id, "подключение", "Подключение...")

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

                cmd = build_ffmpeg_cmd(url, route_id, mode, ff_cfg, str(project_root / hls_cache))
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

echo "  ✔ app/workers/hls_worker.py (создание директорий + абсолютные пути)"

# ------------------------------------------------------------
# Проверка
# ------------------------------------------------------------
if [ ! -s "$PROJECT_DIR/app/workers/hls_worker.py" ]; then
  echo "❌ ОШИБКА: файл пуст или не создан!" >&2
  exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Исправление применено"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что изменилось:"
echo "  • Добавлено создание директории out_dir.mkdir(...) до FFmpeg"
echo "  • Используются абсолютные пути (от корня проекта)"
echo "  • Ошибка 'No such file or directory' больше не появится"
echo ""
echo "🚀 Дальше:"
echo "  1. Остановите бэкенд (Ctrl+C)"
echo "  2. Запустите: python main.py"
echo "  3. В логах появятся строки: 📁 Создана директория: ..."