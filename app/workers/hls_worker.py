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

            try:
                loop = asyncio.get_running_loop()
                codec, profile, pix_fmt = await loop.run_in_executor(
                    None, probe_camera, url, global_cfg
                )
            except Exception:
                codec, profile, pix_fmt = "unknown", "unknown", "unknown"
            # PATCH-124v6: устанавливаем статус на основе ffprobe
            if codec and codec != "unknown":
                logger.info("✅ %s: поток доступен (codec=%s)", route_id, codec)
                manager.set_status(route_id, "в_сети", "Поток активен",
                    metrics={"codec": codec, "profile": profile})
            else:
                logger.warning("⚠️ %s: поток недоступен (codec=unknown)", route_id)
                manager.set_status(route_id, "недоступна", "Кодек не определён")
                await asyncio.sleep(min(backoff * 2, 15))
                backoff = min(backoff * 2, 15)
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
                    # PATCH-122v4: таймаут подключения — ждём первый кадр,
                    # завершение процесса или connect_timeout секунд
                    return_code = await proc.wait()  # PATCH-125v2
                    _we = asyncio.ensure_future(proc.wait())
                    _done, _pending = await asyncio.wait(
                        [_wf, _we],
                        timeout=connect_timeout,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    if _we in _done:
                        # процесс завершился сам (ошибка или успех)
                        return_code = _we.result()
                    elif _wf in _done:
                        # первый кадр получен — поток активен
                        return_code = await proc.wait()
                    else:
                        # таймаут: ffmpeg завис без кадров
                        logger.warning("⏱ %s: нет кадров за %s с — таймаут", route_id, connect_timeout)
                        try:
                            proc.kill()
                        except ProcessLookupError:
                            pass
                        return_code = await proc.wait()
                        log_task.cancel()
                        for _t in (_wf, _we):
                            if not _t.done():
                                _t.cancel()
                        manager.set_status(route_id, "недоступна",
                                           f"Таймаут подключения ({connect_timeout} с)")
                        backoff = min(backoff * 2, backoff_max)
                        await asyncio.sleep(backoff)
                        continue
                    for _t in (_wf, _we):
                        if not _t.done():
                            _t.cancel()

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
        # ИСПРАВЛЕНО (v33): cleanup не удаляет статус, а сохраняет
        # его как «недоступна» (см. обновлённый stream_manager.py).
        manager.cleanup(route_id)
        logger.info("🧹 Воркер завершён: %s", route_id)
