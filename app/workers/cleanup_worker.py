# -*- coding: utf-8 -*-
"""
app/workers/cleanup_worker.py
=============================
Фоновая задача очистки кэша сегментов.

ИСПРАВЛЕНО: ключи конфигурации теперь английские.
"""
import logging
import time
from pathlib import Path

from app.config import config

logger = logging.getLogger(__name__)


def cleanup_worker() -> None:
    """Бесконечный цикл очистки кэша сегментов."""
    while True:
        try:
            cfg = config.all()
            # ИСПРАВЛЕНО: английский ключ конфига.
            clean_cfg = cfg.get("cleanup", {})
            if not clean_cfg.get("enabled", True):
                time.sleep(60)
                continue

            # ИСПРАВЛЕНО: английский ключ конфига.
            hls_cache = cfg.get("paths", {}).get("hls_cache", "hls_cache")
            cache_dir = Path(hls_cache)
            if not cache_dir.is_dir():
                time.sleep(300)
                continue

            now = time.time()
            # ИСПРАВЛЕНО: английский ключ конфига.
            max_age_sec = clean_cfg.get("max_age_hours", 24) * 3600

            for cam_dir in cache_dir.iterdir():
                if not cam_dir.is_dir():
                    continue
                for stream_dir in cam_dir.iterdir():
                    if not stream_dir.is_dir():
                        continue
                    for f in stream_dir.iterdir():
                        if f.suffix == ".ts" and (now - f.stat().st_mtime) > max_age_sec:
                            try:
                                f.unlink()
                            except OSError:
                                pass
                    try:
                        if not any(stream_dir.iterdir()):
                            stream_dir.rmdir()
                    except OSError:
                        pass
        except Exception as e:
            logger.warning("Ошибка очистки кэша: %s", e)

        # ИСПРАВЛЕНО: английский ключ конфига.
        interval = config.get("cleanup", "interval_seconds", default=300)
        time.sleep(interval)
