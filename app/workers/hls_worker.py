# -*- coding: utf-8 -*-
"""
app/workers/hls_worker.py
=========================
Воркер захвата одного потока камеры.

ИСПРАВЛЕНО (v33):
• При отключении камеры воркер завершается штатно и устанавливает
  статус «недоступна» — фронтенд сразу показывает правильный статус
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

    # Создаём директорию для сегментов.
    project_root = Path(__file__).parent.parent.parent
    out_dir = project_root / hls_cache / "camera" / route_id
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error("❌ Не удалось создать директорию %s: %s", out_dir, e)
        return

    logger.info("🔍 Воркер запущен: %s", route_id)
    current_proc = None  # PATCH-132: ссылка на активный ffmpeg процесс
    try:
        while True:
            cam = camera_service.get_camera(cam_id)
            if not cam or not cam.enabled:
                logger.info("⏹ Камера отключена, воркер завершается: %s", route_id)
                # ИСПРАВЛЕНО (v33): устанавливаем статус «недоступна»
                # при штатном завершении, чтобы фронтенд сразу
                # показал правильный статус без мигания.
                manager.set_status(route_id, "недоступна", "Камера отключена")
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

            # PATCH-131: retry для probe_camera
            codec, profile, pix_fmt = "unknown", "unknown", "unknown"
            for _attempt in range(2):  # 2 попытки
                try:
                    loop = asyncio.get_running_loop()
                    codec, profile, pix_fmt = await loop.run_in_executor(
                        None, probe_camera, url, global_cfg
                    )
                    if codec and codec != "unknown":
                        break  # успех
                    if _attempt == 0:
                        logger.info("🔄 %s: ffprobe retry (пауза 3 сек)", route_id)
                        await asyncio.sleep(3)  # PATCH-132: больше пауза между retry
                except Exception:
                    if _attempt == 0:
                        await asyncio.sleep(1)
            # PATCH-124v6: устанавливаем статус на основе ffprobe
            if codec and codec != "unknown":
                logger.info("✅ %s: поток доступен (codec=%s)", route_id, codec)
                manager.set_status(route_id, "в_сети", "Поток активен",
                    metrics={"codec": codec, "profile": profile})
            else:
                logger.warning("⚠️ %s: поток недоступен (codec=unknown)", route_id)
                manager.set_status(route_id, "недоступна", "Кодек не определён")
                # PATCH-131: увеличенный backoff (камера "остывает" после kill)
                backoff = max(backoff, 15)  # минимум 15 сек
                backoff = min(backoff * 2, 30)
                await asyncio.sleep(backoff)
                continue

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
                    # ИСПРАВЛЕНО (v33): устанавливаем статус при
                    # отключении камеры внутри цикла.
                    manager.set_status(route_id, "недоступна", "Камера отключена")
                    break
                manager.set_status(route_id, "подключение", "Запуск потока...")

                cmd = build_ffmpeg_cmd(url, route_id, mode, ff_cfg, str(project_root / hls_cache))

                # Если у камеры audio=false, добавляем флаг -an.
                if not cam.audio:
                    filtered = []
                    skip_next = False
                    for i, arg in enumerate(cmd):
                        if skip_next:
                            skip_next = False
                            continue
                        if arg in ("-c:a", "-b:a", "-ar", "-ac"):
                            skip_next = True
                            continue
                        filtered.append(arg)
                    try:
                        f_index = filtered.index("-f")
                        filtered.insert(f_index, "-an")
                    except ValueError:
                        filtered.append("-an")
                    cmd = filtered
                    logger.info("🔇 %s: аудио отключено", route_id)

                try:
                    # PATCH-131: задержка 1 сек (camera cooldown)
                    await asyncio.sleep(1)
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                    )
                    current_proc = proc  # PATCH-132

                    # PATCH-130: ffmpeg запущен — сразу статус 'в_сети'.
                    # Без этого внутренний цикл сбрасывает на 'подключение',
                    # и PATCH-123 скрывает video → чёрный экран.
                    manager.set_status(route_id, "в_сети", "Поток запущен, ожидание первого кадра")

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
                    return_code = await proc.wait()  # PATCH-125v2
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
        # ИСПРАВЛЕНО (v33): при отмене (например, при выключении камеры
        # через контекстное меню) устанавливаем статус «недоступна».
        manager.set_status(route_id, "недоступна", "Камера отключена")
    finally:
        # PATCH-133: гарантированный kill текущего ffmpeg процесса
        if current_proc is not None:
            try:
                if current_proc.returncode is None:
                    current_proc.kill()
                    try:
                        await current_proc.wait()
                    except Exception:
                        pass
                    logger.info("💀 %s: ffmpeg процесс убит", route_id)
            except Exception as e:
                logger.warning("⚠️ %s: ошибка kill: %s", route_id, e)

        # PATCH-133: дополнительная очистка через psutil / wmic / pkill
        try:
            import psutil
            for p in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = " ".join(p.info.get('cmdline') or [])
                    if f"hls_cache/camera/{route_id}" in cmdline:
                        p.kill()
                        logger.info("💀 %s: psutil убил PID %s", route_id, p.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            try:
                import subprocess as _sp
                import sys as _sys
                if _sys.platform == "win32":
                    # Windows: wmic для kill по cmdline
                    _sp.run(
                        f'wmic process where "CommandLine like '%{route_id}%'" '
                        f'call terminate',
                        shell=True, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL, timeout=3
                    )
                else:
                    # Unix: pkill
                    _sp.run(
                        ["pkill", "-9", "-f", f"hls_cache/camera/{route_id}"],
                        stderr=_sp.DEVNULL, timeout=2
                    )
            except Exception:
                pass  # все fallbacks не сработали

        manager.cleanup(route_id)
        logger.info("🧹 Воркер завершён: %s", route_id)
