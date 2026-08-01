"""
Пробинг камер, определение кодеков, выбор режима (copy/transcode) и GPU-энкодера.
"""
import json
import subprocess
import logging

from .utils import get_ffprobe_path, get_ffmpeg_path
from state import CFG

logger = logging.getLogger(__name__)


def detect_gpu_encoder():
    """Определение доступного GPU-энкодера (NVENC/QSV/AMF/CPU)."""
    out = ""
    try:
        out = subprocess.check_output(
            [get_ffmpeg_path() or "ffmpeg", "-hide_banner", "-encoders"],
            stderr=subprocess.STDOUT, text=True, timeout=3
        ).lower()
        if "h264_nvenc" in out:
            if subprocess.run(
                [get_ffmpeg_path() or "ffmpeg", "-f", "lavfi", "-i",
                 "testsrc=duration=1:size=320x240:rate=1",
                 "-c:v", "h264_nvenc", "-preset", "p1", "-tune", "ll",
                 "-f", "null", "-"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
            ).returncode == 0:
                return "h264_nvenc", ["-preset", "p1", "-tune", "ll"]
    except Exception:
        pass

    if "h264_qsv" in out:
        return "h264_qsv", ["-preset", "fast"]
    if "h264_amf" in out:
        return "h264_amf", ["-usage", "ultralowlatency"]

    return "libx264", ["-preset", "ultrafast", "-tune", "zerolatency"]


def decide_stream_mode(codec, profile, pix_fmt):
    """Решение: copy или transcode."""
    return "copy" if (codec == "h264" and "yuv420p" in pix_fmt) else "transcode"


def probe_camera(url):
    """Получение информации о кодеке камеры через ffprobe."""
    ffprobe_bin = get_ffprobe_path() or "ffmpeg"
    cfg_ff = CFG.get("ffmpeg", {}).get("global", {})

    cmd = [
        ffprobe_bin, "-v", "error",
        "-show_entries", "stream=codec_name,profile,pix_fmt",
        "-of", "json", "-select_streams", "v:0",
        "-analyzeduration", str(cfg_ff.get("probe_analyze_duration", 1000000)),
        "-probesize", str(cfg_ff.get("probe_size", 1000000)),
        "-timeout", str(cfg_ff.get("probe_timeout", 3)),
        url
    ]

    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=cfg_ff.get("probe_timeout", 3)
        )
        if res.returncode == 0 and res.stdout:
            # ✅ ИСПРАВЛЕНО: Теперь корректно извлекаем все три поля
            data = json.loads(res.stdout)
            streams = data.get("streams", [])
            if streams:
                stream = streams[0]
                codec = stream.get("codec_name", "unknown")
                profile = stream.get("profile", "unknown")
                pix_fmt = stream.get("pix_fmt", "unknown")
                logger.info(f"Probe result: codec={codec}, profile={profile}, pix_fmt={pix_fmt}")
                return codec, profile, pix_fmt
    except Exception as e:
        logger.warning(f"Probe failed: {e}")

    return "unknown", "unknown", "unknown"