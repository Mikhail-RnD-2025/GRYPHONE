"""
Stream Engine Module
Управление жизненным циклом видеопотоков, FFmpeg HLS-генерация, fallback-логика.
"""

from .utils import (
    get_ffmpeg_path,
    get_ffprobe_path,
    terminate_proc,
    cleanup_orphaned_ffmpeg,
)
from .probe import probe_camera, decide_stream_mode
from .builder import build_ffmpeg_cmd
from .worker import hls_worker_async

__all__ = [
    "get_ffmpeg_path",
    "get_ffprobe_path",
    "terminate_proc",
    "cleanup_orphaned_ffmpeg",
    "probe_camera",
    "decide_stream_mode",
    "build_ffmpeg_cmd",
    "hls_worker_async",
]