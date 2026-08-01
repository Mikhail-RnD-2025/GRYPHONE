def default_cfg():
    return {
        "server": {"host": "0.0.0.0", "port": 5000},
        "paths": {"hls_cache": "hls_cache"},
        "ffmpeg": {
            "mode": "auto",
            "logging": {"level": "info", "stats_period": 1, "hide_banner": True, "generate_report": False},
            "global": {
                "transport": "tcp", "buffer_mode": "nobuffer", "error_detection": "ignore_err", "threads": 0,
                "probe_timeout": 3, "probe_analyze_duration": 1000000, "probe_size": 1000000,
                "hls_time": 2, "hls_list_size": 6,
                "hls_flags": "delete_segments+temp_file+program_date_time+split_by_time+append_list",
                "hls_segment_type": "fmp4", "hls_fmp4_init_filename": "init.mp4", "flush_packets": True,
                "rtsp_connect_timeout": 8, "startup_timeout": 15.0, "startup_check_interval": 1.0,
                "startup_min_m3u8_size": 100
            },
            "hls_player": {"maxBufferLength": 3, "maxMaxBufferLength": 4, "maxBufferSizeMB": 8,
                           "backBufferLength": 0, "liveSyncDuration": 0.5, "liveMaxLatencyDuration": 1.5},
            "copy": {"note": "Прямой поток"},
            "transcode": {"gpu_encoder": "auto", "video_bitrate": "2500k", "video_maxrate": "4000k",
                          "video_bufsize": "8000k", "gop_size": 30, "keyint_min": 30, "audio_bitrate": "48k",
                          "pix_fmt": "yuv420p", "preset": "ultrafast", "tune": "zerolatency"}
        },
        "app": {"backoff_max": 30, "host_check_timeout": 5.0, "stable_runtime_threshold": 60,
                "gpu_fallback_threshold": 5.0, "cleanup_min_file_size": 512, "default_set": ""},
        "cleanup": {"enabled": True, "interval_seconds": 300, "max_age_hours": 24},
        "performance": {"probe_workers": 32, "sse_interval": 1.0},
        "archive": {"enabled": True, "poll_interval_sec": 2,
                    "pools": [{"id": "pool_main", "path": "archive_main", "max_size_gb": 50},
                              {"id": "pool_backup", "path": "archive_backup", "max_size_gb": 20}]}
    }

def sanitize_camera(raw_cam):
    if not isinstance(raw_cam, dict): return None
    cid, mu = raw_cam.get("id"), raw_cam.get("main_url")
    if cid is None or (isinstance(cid, str) and not cid.strip()) or not isinstance(cid, (str, int)): return None
    if not mu or not isinstance(mu, str): return None
    raw_en = raw_cam.get("enabled", True)
    en = True if raw_en is True else False if raw_en is False else (raw_en.strip().lower() not in ("false","0","no","") if isinstance(raw_en, str) else (raw_en != 0 if isinstance(raw_en, (int,float)) else True))
    su = raw_cam.get("sub_url")
    return {"id": str(cid).strip(), "name": str(raw_cam.get("name", f"Camera {cid}")),
            "main_url": str(mu).strip(), "sub_url": str(mu if su is None or su.strip()=="" else su).strip(),
            "enabled": bool(en), "comment": str(raw_cam.get("comment", ""))}

def merge_dicts(base, override):
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict): merge_dicts(base[k], v)
        else: base[k] = v