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
