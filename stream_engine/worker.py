"""
Асинхронный воркер: управление жизненным циклом потока, парсинг логов, 3-stage fallback.
"""
import os
import re
import time
import asyncio
import logging
import subprocess
from pathlib import Path
from collections import deque

from state import STATE_LOCK, LOGS_LOCK, ACTIVE_PROCS_LOCK, CFG, CAMERAS_DB, ASYNC_TASKS, ACTIVE_PROCS, PROBE_EXECUTOR, STREAM_STATS, FFMPEG_LOGS
from .utils import _cleanup_hls_dir, terminate_proc, _check_host
from .probe import probe_camera, decide_stream_mode
from .builder import build_ffmpeg_cmd

logger = logging.getLogger(__name__)
STATS_REGEX = re.compile(r"frame=\s*(\d+)\s*fps=\s*([\d.]+|N/A)\s*q=\s*([\d.-]+|N/A)\s*size=\s*(\S+)\s*time=(\S+)\s*bitrate=(\S+)")


async def _read_stderr_logs(proc, route_id):
    try:
        while True:
            try:
                line = await asyncio.wait_for(proc.stderr.readline(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            if not line:
                break
            ls = line.decode('utf-8', 'ignore').strip()
            if not ls:
                continue
            async with LOGS_LOCK:
                if route_id in FFMPEG_LOGS:
                    FFMPEG_LOGS[route_id].append(f"[{time.strftime('%H:%M:%S')}] {ls}")
            match = STATS_REGEX.search(ls)
            if match:
                async with STATE_LOCK:
                    if route_id in STREAM_STATS:
                        STREAM_STATS[route_id]['metrics'] = {
                            'fps': match.group(2) if match.group(2) != 'N/A' else '--',
                            'bitrate': match.group(6) if match.group(6) != 'N/A' else '--',
                            'time': match.group(5) if match.group(5) != 'N/A' else '--'
                        }
    except Exception:
        pass


async def _wait_for_m3u8(proc, m3u8_path, g_cfg, launch_time):
    timeout = float(g_cfg.get("startup_timeout", 15.0))
    interval = float(g_cfg.get("startup_check_interval", 1.0))
    min_size = int(g_cfg.get("startup_min_m3u8_size", 100))
    max_checks = max(1, int(timeout / max(0.1, interval)))
    min_mtime = launch_time - 0.5
    for _ in range(max_checks):
        if proc.returncode is not None:
            return False
        if m3u8_path.exists():
            try:
                st = m3u8_path.stat()
                if st.st_mtime >= min_mtime and st.st_size >= min_size:
                    return True
            except OSError:
                pass
        await asyncio.sleep(interval)
    return False


async def hls_worker_async(url, route_id, cam_id):
    """Основной асинхронный цикл воркера для одной камеры."""
    cfg = CFG
    hls_dir_base = (Path(cfg["paths"]["hls_cache"]) / "camera" / route_id).resolve()
    hls_dir_base.mkdir(parents=True, exist_ok=True)

    backoff = 1
    attempt_count = 0
    loop = asyncio.get_running_loop()

    logger.info(f"🔍 {route_id} | Инициализация...")
    async with LOGS_LOCK:
        FFMPEG_LOGS[route_id] = deque([f"[{time.strftime('%H:%M:%S')}] 🔄 Воркер запущен"], maxlen=500)

    try:
        while True:
            app_cfg = CFG["app"]
            if not CAMERAS_DB.get(cam_id, {}).get("enabled"):
                break

            if attempt_count == 0:
                STREAM_STATS[route_id] = {
                    "state": "checking", "msg": "Первичная проверка...",
                    "metrics": {"fps": "--", "bitrate": "--", "time": "00:00:00"}
                }

            if not await _check_host(url, timeout=app_cfg.get("host_check_timeout", 5.0)):
                logger.warning(f"⚠️ {route_id}: Host unreachable")
                async with LOGS_LOCK:
                    FFMPEG_LOGS.setdefault(route_id, deque(maxlen=500)).append(
                        f"[{time.strftime('%H:%M:%S')}] ⚠️ Host unreachable"
                    )
                async with STATE_LOCK:
                    STREAM_STATS[route_id] = {
                        "state": "err", "msg": "Недоступна",
                        "metrics": {"fps": "--", "bitrate": "--", "time": "00:00:00"}
                    }
                attempt_count += 1
                await asyncio.sleep(min(backoff * 2, app_cfg.get("backoff_max", 30)))
                backoff = min(backoff * 2, app_cfg.get("backoff_max", 30))
                continue

            attempt_count = 0
            backoff = 1
            async with LOGS_LOCK:
                FFMPEG_LOGS.setdefault(route_id, deque(maxlen=500)).append(
                    f"[{time.strftime('%H:%M:%S')}] 🚀 Запуск потока..."
                )
            if not CAMERAS_DB.get(cam_id, {}).get("enabled"):
                break

            try:
                codec, profile, pix_fmt = await loop.run_in_executor(
                    PROBE_EXECUTOR, probe_camera, url
                )
            except Exception:
                codec, profile, pix_fmt = "unknown", "unknown", "unknown"

            if not CAMERAS_DB.get(cam_id, {}).get("enabled"):
                break

            ff_cfg = CFG.get("ffmpeg", {})
            g_cfg = ff_cfg.get("global", {})
            mode = ff_cfg.get("mode", "auto")
            sm = "copy" if mode == "copy" else (
                "transcode" if mode == "transcode" else decide_stream_mode(codec, profile, pix_fmt)
            )
            logger.info(f"✅ {route_id}: {sm.upper()} (codec: {codec})")

            while True:
                if not CAMERAS_DB.get(cam_id, {}).get("enabled"):
                    break
                if attempt_count == 0:
                    STREAM_STATS[route_id] = {
                        "state": "checking", "msg": "Установка RTSP...",
                        "metrics": STREAM_STATS[route_id].get("metrics", {})
                    }

                hls_dir = (Path(CFG["paths"]["hls_cache"]) / "camera" / route_id).resolve()
                _cleanup_hls_dir(hls_dir)
                hls_dir.mkdir(parents=True, exist_ok=True)
                m3u8_path = hls_dir / "index.m3u8"

                old_proc_to_kill = None
                async with ACTIVE_PROCS_LOCK:
                    old_proc_to_kill = ACTIVE_PROCS.get(route_id)
                    ACTIVE_PROCS[route_id] = None
                if old_proc_to_kill and old_proc_to_kill.returncode is None:
                    await terminate_proc(old_proc_to_kill, route_id)

                stream_id = f"{int(time.time())}_{os.getpid()}"
                launch_time = time.time()
                cmd, _ = build_ffmpeg_cmd(url, route_id, sm, stream_id=stream_id)

                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, cwd=str(hls_dir)
                    )
                    logger.info(f"🎥 {route_id} | FFmpeg PID: {proc.pid}, CWD: {hls_dir}")
                    async with ACTIVE_PROCS_LOCK:
                        ACTIVE_PROCS[route_id] = proc

                    log_task = asyncio.create_task(_read_stderr_logs(proc, route_id))
                    startup_success = await _wait_for_m3u8(proc, m3u8_path, g_cfg, launch_time)

                    if startup_success:
                        success = True
                        rc = await proc.wait()
                        log_task.cancel()
                        async with STATE_LOCK:
                            STREAM_STATS[route_id] = {
                                "state": "ok", "msg": "Поток активен",
                                "metrics": STREAM_STATS[route_id].get("metrics", {})
                            }
                        if rc != 0:
                            success = False
                            logger.warning(f"⚠️ {route_id} | FFmpeg died (exit {rc})")
                    else:
                        log_task.cancel()
                        await terminate_proc(proc, route_id)
                        success = False
                        rc = proc.returncode if proc.returncode is not None else -1

                    # Stage 1 (GPU alt)
                    if not success and rc != 0:
                        logger.warning(f"🔄 {route_id} | Stage 0 failed (exit {rc}), trying Stage 1...")
                        _cleanup_hls_dir(hls_dir)
                        hls_dir.mkdir(parents=True, exist_ok=True)
                        old_proc_to_kill = None
                        async with ACTIVE_PROCS_LOCK:
                            old_proc_to_kill = ACTIVE_PROCS.get(route_id)
                            ACTIVE_PROCS[route_id] = None
                        if old_proc_to_kill and old_proc_to_kill.returncode is None:
                            await terminate_proc(old_proc_to_kill, route_id)
                        stream_id = f"{int(time.time())}_{os.getpid()}"
                        launch_time = time.time()
                        cmd, _ = build_ffmpeg_cmd(
                            url, route_id, "transcode",
                            force_cpu=False, force_software_decode=True, stream_id=stream_id
                        )
                        proc = await asyncio.create_subprocess_exec(
                            *cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, cwd=str(hls_dir)
                        )
                        async with ACTIVE_PROCS_LOCK:
                            ACTIVE_PROCS[route_id] = proc
                        log_task = asyncio.create_task(_read_stderr_logs(proc, route_id))
                        startup_success = await _wait_for_m3u8(proc, m3u8_path, g_cfg, launch_time)
                        if startup_success:
                            success = True
                            rc = await proc.wait()
                            log_task.cancel()
                        else:
                            log_task.cancel()
                            await terminate_proc(proc, route_id)
                            rc = proc.returncode if proc.returncode is not None else -1

                    # Stage 2 (CPU fallback)
                    if not success:
                        logger.warning(f"🔄 {route_id} | Stage 1 failed (exit {rc}), trying Stage 2 (libx264)...")
                        _cleanup_hls_dir(hls_dir)
                        hls_dir.mkdir(parents=True, exist_ok=True)
                        old_proc_to_kill = None
                        async with ACTIVE_PROCS_LOCK:
                            old_proc_to_kill = ACTIVE_PROCS.get(route_id)
                            ACTIVE_PROCS[route_id] = None
                        if old_proc_to_kill and old_proc_to_kill.returncode is None:
                            await terminate_proc(old_proc_to_kill, route_id)
                        stream_id = f"{int(time.time())}_{os.getpid()}"
                        launch_time = time.time()
                        cmd, _ = build_ffmpeg_cmd(
                            url, route_id, "transcode",
                            force_cpu=True, force_software_decode=False, stream_id=stream_id
                        )
                        proc = await asyncio.create_subprocess_exec(
                            *cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, cwd=str(hls_dir)
                        )
                        async with ACTIVE_PROCS_LOCK:
                            ACTIVE_PROCS[route_id] = proc
                        log_task = asyncio.create_task(_read_stderr_logs(proc, route_id))
                        startup_success = await _wait_for_m3u8(proc, m3u8_path, g_cfg, launch_time)
                        if startup_success:
                            success = True
                            rc = await proc.wait()
                            log_task.cancel()
                        else:
                            log_task.cancel()
                            await terminate_proc(proc, route_id)
                            success = False
                        if not success:
                            logger.error(f"❌ {route_id} | All 3 stages failed. Last exit code: {rc}")

                except Exception as e:
                    success = False
                    rc = -1
                    err = str(e).lower()
                    if "invalid argument" in err or "exit 4294967274" in err:
                        logger.error(f"❌ {route_id} | FFmpeg config error: {e}")
                    elif "permission" in err or "access denied" in err:
                        logger.error(f"❌ {route_id} | File access error: {e}")
                    else:
                        logger.error(f"❌ {route_id} | Crash: {e}")

                if not success:
                    logger.warning(f"🔁 {route_id} | Exit {rc}")
                    async with LOGS_LOCK:
                        FFMPEG_LOGS.setdefault(route_id, deque(maxlen=500)).append(
                            f"[{time.strftime('%H:%M:%S')}] ❌ FFmpeg exit code: {rc}"
                        )
                    async with STATE_LOCK:
                        STREAM_STATS[route_id] = {"state": "err", "msg": "Недоступна", "metrics": {}}
                        attempt_count += 1
                else:
                    async with STATE_LOCK:
                        STREAM_STATS[route_id] = {
                            "state": "ok", "msg": "Поток активен",
                            "metrics": STREAM_STATS[route_id].get("metrics", {})
                        }
                    attempt_count = 0

                ca = CFG
                backoff = 1 if success else min(backoff * 2, ca["app"]["backoff_max"])
                if not success:
                    await asyncio.sleep(backoff)
                    continue
                break

    except asyncio.CancelledError:
        logger.info(f"🛑 {route_id} cancelled")
    finally:
        async with STATE_LOCK:
            STREAM_STATS.pop(route_id, None)
        async with LOGS_LOCK:
            ASYNC_TASKS.pop(route_id, None)
            FFMPEG_LOGS.setdefault(route_id, deque(maxlen=500)).append(
                f"[{time.strftime('%H:%M:%S')}] 🧹 Воркер остановлен"
            )
        async with ACTIVE_PROCS_LOCK:
            ACTIVE_PROCS.pop(route_id, None)
        logger.info(f"🧹 {route_id} cleaned")