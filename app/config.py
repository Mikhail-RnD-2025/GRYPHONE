# -*- coding: utf-8 -*-
"""
app/config.py
=============
Управление конфигурацией приложения.

ДОБАВЛЕНО: метод update() для изменения конфигурации извне (например,
через API). Это исправляет ошибку, при которой сохранение конфига
не обновляло данные.
"""
import copy
import logging
from typing import Any, Dict

from app.database import db

logger = logging.getLogger(__name__)


def default_config() -> Dict[str, Any]:
    """Возвращает конфигурацию по умолчанию."""
    return {
        "server": {"host": "0.0.0.0", "port": 5000},
        "paths": {
            "cameras_db": "rtsp_viewer.db",
            "sets_db": "rtsp_viewer.db",
            "hls_cache": "hls_cache",
        },
        "ffmpeg": {
            "mode": "auto",
            "logging": {"level": "info", "stats_period": 1,
                        "hide_banner": True, "generate_report": False},
            "global": {
                "transport": "tcp", "buffer_mode": "nobuffer",
                "error_detection": "ignore_err", "threads": 0,
                "probe_timeout": 3, "probe_analyze_duration": 1000000,
                "probe_size": 1000000, "hls_time": 2, "hls_list_size": 4,
                "hls_flags": "delete_segments+temp_file+program_date_time",
            },
            "copy": {"note": "Прямой поток"},
            "transcode": {
                "gpu_encoder": "auto", "video_bitrate": "2500k",
                "video_maxrate": "4000k", "video_bufsize": "8000k",
                "gop_size": 30, "keyint_min": 30, "audio_bitrate": "48k",
                "pix_fmt": "yuv420p", "preset": "ultrafast", "tune": "zerolatency",
            },
        },
        "app": {
            "backoff_max": 30, "stable_runtime_threshold": 60,
            "gpu_fallback_threshold": 5.0, "cleanup_min_file_size": 512,
            "default_set": "",
        },
        "cleanup": {"enabled": True, "interval_seconds": 300, "max_age_hours": 24},
        "performance": {"probe_workers": 32, "sse_interval": 1.0},
        "events": {"enabled": True, "retention_days": 30, "db_path": "rtsp_viewer.db"},
        "storage": {"default": "", "targets": []},
        "integration": {"enabled": False},
        "analytics": {"enabled": False},
        "cluster": {"enabled": False},
    }


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Рекурсивно сливает ``override`` в ``base``."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class ConfigManager:
    """Доступ к конфигурации приложения."""

    KEY = "config"

    def __init__(self):
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """Загружает сохранённую конфигурацию и сливает с дефолтной."""
        saved = db.get(self.KEY, {}) or {}
        return _deep_merge(default_config(), saved)

    def reload(self) -> None:
        """Перечитывает конфигурацию из БД."""
        self._data = self._load()

    def save(self) -> None:
        """Сохраняет текущую конфигурацию в БД."""
        db.save(self.KEY, self._data)

    # ДОБАВЛЕНО: метод для обновления конфигурации извне.
    def update(self, new_data: Dict[str, Any]) -> None:
        """Обновляет конфигурацию из словаря (слияние с текущей).

        Используется в API для сохранения изменений конфигурации.
        """
        self._data = _deep_merge(self._data, new_data)

    def all(self) -> Dict[str, Any]:
        """Возвращает полную конфигурацию (копию)."""
        return copy.deepcopy(self._data)

    def get(self, *path: str, default: Any = None) -> Any:
        """Возвращает параметр по пути."""
        node: Any = self._data
        for key in path:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return copy.deepcopy(node)

    def section(self, name: str) -> Dict[str, Any]:
        """Возвращает целую секцию конфигурации (копию)."""
        value = self._data.get(name, {})
        return copy.deepcopy(value) if isinstance(value, dict) else {}


config = ConfigManager()
