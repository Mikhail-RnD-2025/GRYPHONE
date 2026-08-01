"""
Утилиты: поиск исполняемых файлов, очистка каталогов, управление процессами, проверка сети.
"""
import os
import sys
import shutil
import asyncio
import logging
import urllib.parse
import subprocess
from pathlib import Path

from state import ACTIVE_PROCS, ACTIVE_PROCS_LOCK

logger = logging.getLogger(__name__)


def get_ffmpeg_path():
    """Поиск пути к ffmpeg в PATH или в папке приложения."""
    if getattr(sys, 'frozen', False):
        path = os.path.join(
            getattr(sys, '_MEIPASS', os.path.abspath('.')),
            "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
        )
        if os.path.exists(path):
            return path
    return shutil.which("ffmpeg")


def get_ffprobe_path():
    return shutil.which("ffprobe") or get_ffmpeg_path()


def _cleanup_hls_dir(hls_dir):
    """Очистка HLS-директории от старых сегментов."""
    if hls_dir.exists():
        for f in hls_dir.iterdir():
            if f.is_file() and f.suffix in ('.m4s', '.mp4', '.m3u8', '.tmp', '.ts'):
                try:
                    f.unlink()
                except OSError:
                    pass


async def terminate_proc(proc, route_id="unknown"):
    """Корректное завершение процесса FFmpeg."""
    if proc.returncode is None:
        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=2)
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ {route_id} | FFmpeg PID {proc.pid} not responding, killing...")
                try:
                    proc.kill()
                    await asyncio.wait_for(proc.wait(), timeout=2)
                except Exception as e:
                    logger.error(f"❌ {route_id} | Failed to kill FFmpeg: {e}")
        except ProcessLookupError:
            pass
        except Exception as e:
            logger.error(f"❌ {route_id} | Failed to terminate: {e}")


async def _check_host(url, timeout=2.0):
    """Проверка доступности хоста камеры."""
    try:
        parsed = urllib.parse.urlparse(url)
        host, port = parsed.hostname, parsed.port or 554
        if not host:
            return False
        r, w = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        w.close()
        await w.wait_closed()
        return True
    except Exception:
        return False


async def cleanup_orphaned_ffmpeg():
    """Удаление зависших процессов ffmpeg."""
    try:
        if os.name == 'nt':
            res = await asyncio.to_thread(
                subprocess.run,
                ['tasklist', '/FI', 'IMAGENAME eq ffmpeg.exe', '/FO', 'CSV'],
                capture_output=True, text=True, timeout=5
            )
            if 'ffmpeg.exe' in res.stdout:
                logger.warning("⚠️ Found orphaned ffmpeg.exe, killing...")
                await asyncio.to_thread(
                    subprocess.run,
                    ['taskkill', '/F', '/IM', 'ffmpeg.exe'],
                    capture_output=True, timeout=5
                )
                await asyncio.sleep(1)
        else:
            await asyncio.to_thread(
                subprocess.run,
                ['pkill', '-9', '-f', 'ffmpeg'],
                capture_output=True, timeout=5
            )
            await asyncio.sleep(1)
    except Exception as e:
        logger.warning(f"⚠️ Failed to cleanup orphaned FFmpeg: {e}")