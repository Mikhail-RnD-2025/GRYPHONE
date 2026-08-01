"""
Генерация CLI-команд FFmpeg для HLS-генерации с учётом GPU/CPU fallback.
"""
import logging
from pathlib import Path

from state import CFG
from .utils import get_ffmpeg_path
from .probe import detect_gpu_encoder

logger = logging.getLogger(__name__)


def build_ffmpeg_cmd(cam_url, route_id, stream_mode, force_cpu=False, force_software_decode=False, stream_id=None):
    """Формирование команды запуска FFmpeg."""
    ff_cfg = CFG.get("ffmpeg", {})
    g = ff_cfg.get("global", {})

    # Базовые параметры
    cmd = [get_ffmpeg_path() or "ffmpeg", "-nostdin", "-stats", "-loglevel", "verbose"]
    if ff_cfg.get("logging", {}).get("hide_banner", True):
        cmd.append("-hide_banner")
    cmd.extend(["-timeout", str(g.get("rtsp_connect_timeout", 8))])

    t = ff_cfg.get("transcode", {})
    enc = "libx264" if force_cpu else t.get("gpu_encoder", "auto")
    use_qsv_hw_decode = False

    # Проверка аппаратного ускорения
    if not force_cpu and stream_mode != "copy" and not force_software_decode:
        if enc == "h264_qsv":
            use_qsv_hw_decode = True
        elif enc == "auto":
            detected_enc, _ = detect_gpu_encoder()
            use_qsv_hw_decode = (detected_enc == "h264_qsv")

    if use_qsv_hw_decode:
        cmd.extend([
            "-init_hw_device", "qsv=hw,child_device_type=dxva2",
            "-filter_hw_device", "hw",
            "-hwaccel", "qsv",
            "-hwaccel_output_format", "qsv"
        ])

    # Параметры входа
    cmd.extend([
        "-rtsp_transport", g.get("transport", "tcp"),
        "-fflags", f"{g.get('buffer_mode','nobuffer')}+discardcorrupt+genpts+igndts",
        "-flags", "low_delay+global_header",
        "-err_detect", g.get("error_detection", "ignore_err"),
        "-threads", str(g.get("threads", 0)),
        "-max_delay", "500000",
        "-i", cam_url
    ])

    # Параметры кодирования
    if stream_mode == "copy":
        # ✅ РЕЖИМ COPY: только копирование, БЕЗ фильтров формата
        cmd += [
            "-c:v", "copy",
            "-c:a", "copy",
            "-avoid_negative_ts", "make_zero",
            "-reset_timestamps", "1"
        ]
    else:
        if enc == "auto" and not force_cpu:
            enc, _ = detect_gpu_encoder()

        if enc == "h264_qsv":
            cmd += [
                "-vf", "setpts=PTS-STARTPTS,scale_qsv=format=nv12" if use_qsv_hw_decode else "setpts=PTS-STARTPTS,format=nv12,hwupload=extra_hw_frames=64",
                "-c:v", "h264_qsv", "-preset", "veryfast"
            ] + (
                ["-global_quality", "23", "-rc:v", "cbr", "-keyint_min", str(t.get("keyint_min", 30)), "-bf", "0", "-refs", "1", "-look_ahead", "0"]
                if use_qsv_hw_decode
                else ["-keyint_min", str(t.get("keyint_min", 30)), "-bf", "0", "-refs", "1"]
            ) + [
                "-b:v", t.get("video_bitrate", "2500k"),
                "-maxrate", t.get("video_maxrate", "4000k"),
                "-bufsize", t.get("video_bufsize", "8000k"),
                "-g", str(t.get("gop_size", 30)),
                "-c:a", "aac", "-b:a", t.get("audio_bitrate", "48k")
            ]
        elif enc == "h264_nvenc":
            cmd += [
                "-vf", "setpts=PTS-STARTPTS",
                "-c:v", "h264_nvenc", "-preset", "p1", "-tune", "ll",
                "-b:v", t.get("video_bitrate", "2500k"),
                "-maxrate", t.get("video_maxrate", "4000k"),
                "-bufsize", t.get("video_bufsize", "8000k"),
                "-g", str(t.get("gop_size", 30)),
                "-pix_fmt", "yuv420p",  # ✅ Только для транскодирования
                "-c:a", "aac", "-b:a", t.get("audio_bitrate", "48k")
            ]
        elif enc == "h264_amf":
            cmd += [
                "-vf", "setpts=PTS-STARTPTS",
                "-c:v", "h264_amf", "-usage", "ultralowlatency",
                "-b:v", t.get("video_bitrate", "2500k"),
                "-c:a", "aac", "-b:a", t.get("audio_bitrate", "48k")
            ]
        else:
            # libx264 (CPU)
            cmd += [
                "-vf", "setpts=PTS-STARTPTS",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "zerolatency",
                "-b:v", "2500k",
                "-maxrate", "3000k",
                "-bufsize", "5000k",
                "-g", "30",
                "-pix_fmt", "yuv420p",  # ✅ Только для транскодирования
                "-c:a", "aac",
                "-b:a", "64k",
                "-movflags", "+faststart"
            ]

    # Параметры вывода HLS
    hls_dir = (Path(CFG["paths"]["hls_cache"]) / "camera" / route_id).resolve()
    if g.get("flush_packets", True):
        cmd += ["-flush_packets", "1"]

    # ✅ ИСПРАВЛЕНО: УБРАЛИ -pix_fmt и -color_range отсюда!
    # Они теперь только внутри блоков транскодирования выше.
    # В режиме copy они вызывали конфликт и падение FFmpeg.

    hls_seg_type = g.get("hls_segment_type", "mpegts")
    base_flags = g.get("hls_flags", "delete_segments+temp_file+program_date_time")

    if hls_seg_type == "fmp4":
        init_filename = f"init_{stream_id}.mp4" if stream_id else g.get("hls_fmp4_init_filename", "init.mp4")
        cmd += [
            "-f", "hls",
            "-hls_time", str(g.get("hls_time", 2)),
            "-hls_list_size", str(g.get("hls_list_size", 6)),
            "-hls_flags", base_flags,
            "-hls_segment_type", "fmp4",
            "-hls_fmp4_init_filename", init_filename,
            "-hls_segment_filename", "seg_%03d.m4s",
            "-hls_allow_cache", "0",
            "index.m3u8"
        ]
    else:
        cmd += [
            "-f", "hls",
            "-hls_time", str(g.get("hls_time", 2)),
            "-hls_list_size", str(g.get("hls_list_size", 4)),
            "-hls_flags", base_flags,
            "-hls_segment_filename", "seg_%03d.ts",
            "index.m3u8"
        ]

    # ✅ ЛОГИРОВАНИЕ: Выводим полную команду для отладки
    logger.debug(f"FFmpeg command: {' '.join(cmd)}")

    return cmd, hls_dir