# -*- coding: utf-8 -*-
"""
app/config.py
=============

Управление конфигурацией приложения.

ИСТОЧНИК ЭТАЛОНА:  database/sql/default_config.sql
    — внешний SQL-файл с INSERT-командой в таблицу settings.
    При первом запуске читается, JSON извлекается, служебные ключи "_comment"
    удаляются, результат сохраняется в БД под ключом "config".

ПОВЕДЕНИЕ:
    - Первый запуск: SQL -> БД.
    - Последующие запуски: конфиг из БД (пользовательские изменения сохраняются).
    - Если .sql файл недоступен, используется встроенный fallback default_config().

МЕТОД update():
    Позволяет изменять конфигурацию извне (например, через API /api/config/save).
"""

import copy
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict

from app.database import db

# Пути относительно корня проекта
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQL_PATH = BASE_DIR / "database" / "sql" / "default_config.sql"

logger = logging.getLogger(__name__)


def _strip_comments(obj: Any) -> Any:
    """Рекурсивно удаляет служебные ключи '_comment' из структуры."""
    if isinstance(obj, dict):
        return {k: _strip_comments(v) for k, v in obj.items() if k != "_comment"}
    if isinstance(obj, list):
        return [_strip_comments(item) for item in obj]
    return obj


def _load_default_from_sql(sql_path: Path) -> Dict[str, Any]:
    """Читает эталонный конфиг из SQL-файла.

    Парсит JSON из команды INSERT INTO settings ... VALUES ('config', '...JSON...').
    Удаляет служебные ключи '_comment'.
    Возвращает пустой словарь, если файл недоступен или парсинг не удался.
    """
    if not sql_path.is_file():
        logger.warning("SQL-файл конфигурации не найден: %s", sql_path)
        return {}

    try:
        content = sql_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Не удалось прочитать SQL-файл: %s", e)
        return {}

    # Ищем JSON между VALUES ('config', ' и ');
    # Паттерн: VALUES ('config', '...');
    match = re.search(r"VALUES\s*\(\s*'config'\s*,\s*'(.+)'\s*\)\s*;", content, re.DOTALL)
    if not match:
        logger.warning("В SQL-файле не найдена INSERT-команда с ключом 'config'")
        return {}

    json_text = match.group(1)
    # В SQL одинарные кавычки экранируются удвоением '' -> '
    json_text = json_text.replace("''", "'")

    try:
        raw = json.loads(json_text)
    except json.JSONDecodeError as e:
        logger.warning("Не удалось распарсить JSON из SQL-файла: %s", e)
        return {}

    return _strip_comments(raw)


def _fallback_default_config() -> Dict[str, Any]:
    """Запасной вариант конфига на случай недоступности SQL-файла.

    Используется только если database/sql/default_config.sql не найден или битый.
    Содержит минимальный набор параметров, достаточный для запуска.
    """
    return {
        "server": {"host": "0.0.0.0", "port": 5000},
        "paths": {"hls_cache": "hls_cache"},
        "ffmpeg": {
            "mode": "auto",
            "logging": {"level": "info", "stats_period": 1, "hide_banner": True},
            "global": {"transport": "tcp", "buffer_mode": "nobuffer",
                       "probe_timeout": 3, "hls_time": 2, "hls_list_size": 4},
            "transcode": {"gpu_encoder": "auto", "preset": "ultrafast", "tune": "zerolatency"},
        },
        "app": {"backoff_max": 30, "default_set": ""},
        "cleanup": {"enabled": True, "interval_seconds": 300, "max_age_hours": 24},
        "performance": {"probe_workers": 32, "sse_interval": 1.0},
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
    """Доступ к конфигурации приложения.

    Приоритет источников:
        1. Сохранённый в БД конфиг (пользовательский).
        2. Эталон из database/sql/default_config.sql.
        3. Встроенный fallback _fallback_default_config().
    """

    KEY = "config"

    def __init__(self, sql_path: Path = DEFAULT_SQL_PATH):
        self._sql_path = sql_path
        self._default = self._load_default()
        self._data: Dict[str, Any] = self._load()

    def _load_default(self) -> Dict[str, Any]:
        """Загружает эталон: сначала из SQL-файла, затем fallback."""
        default = _load_default_from_sql(self._sql_path)
        if not default:
            logger.warning("Используется запасной default_config (SQL недоступен)")
            default = _fallback_default_config()
        return default

    def _load(self) -> Dict[str, Any]:
        """Загружает сохранённую конфигурацию и сливает с эталонной.

        Если в БД ещё нет ключа 'config' (первый запуск) — сохраняет эталон.
        """
        saved = db.get(self.KEY, None)
        if saved is None or (isinstance(saved, dict) and not saved):
            # Первый запуск: сохраняем эталон в БД
            logger.info("Конфигурация не найдена в БД — инициализирую из SQL-файла")
            db.save(self.KEY, self._default)
            return copy.deepcopy(self._default)
        if not isinstance(saved, dict):
            saved = {}
        # Мержим: пользовательские значения перекрывают эталон,
        # но отсутствующие ключи из эталона добавляются (безопасный апгрейд).
        return _deep_merge(self._default, saved)

    def reload(self) -> None:
        """Перечитывает эталон и конфигурацию."""
        self._default = self._load_default()
        self._data = self._load()

    def save(self) -> None:
        """Сохраняет текущую конфигурацию в БД."""
        db.save(self.KEY, self._data)

    def update(self, new_data: Dict[str, Any]) -> None:
        """Обновляет конфигурацию из словаря (слияние с текущей).

        Используется в API для сохранения изменений конфигурации.
        """
        self._data = _deep_merge(self._data, new_data)

    def all(self) -> Dict[str, Any]:
        """Возвращает полную конфигурацию (копию)."""
        return copy.deepcopy(self._data)

    def get(self, *path: str, default: Any = None) -> Any:
        """Возвращает параметр по пути (например, ``get("server", "port")``)."""
        node: Any = self._data
        for key in path:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return copy.deepcopy(node) if isinstance(node, (dict, list)) else node

    def section(self, name: str) -> Dict[str, Any]:
        """Возвращает целую секцию конфигурации (копию)."""
        value = self._data.get(name, {})
        return copy.deepcopy(value) if isinstance(value, dict) else {}

    @property
    def default_config(self) -> Dict[str, Any]:
        """Возвращает эталонную конфигурацию (без пользовательских правок)."""
        return copy.deepcopy(self._default)


# Глобальный экземпляр менеджера конфигурации.
config = ConfigManager()
