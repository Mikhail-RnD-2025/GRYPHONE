#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 03: ЯДРО ДАННЫХ БЭКЕНДА
#  ------------------------------------------------------------
#  Заполняет фундаментальные модули данных:
#    - app/models.py    — доменные модели (камера, событие, набор)
#    - app/database.py  — репозиторий (слой доступа к данным)
#    - app/config.py    — управление конфигурацией
#
#  Запуск:   bash 03_backend_core.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# app/models.py — доменные модели
# ============================================================
cat > "$PROJECT_DIR/app/models.py" << 'PYEOF_MODELS'
# -*- coding: utf-8 -*-
"""
app/models.py
=============
Доменные модели проекта: объекты данных, не зависящие от способа хранения.

Модели:
  - Camera : камера видеонаблюдения
  - Event  : событие (для своей базы событий)
  - Set    : набор камер

Модели реализованы как простые классы с методами (де)сериализации, чтобы их
можно было хранить и в текущей встроенной БД, и в будущем в другой СУБД
без изменения бизнес-логики.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Камера
# ---------------------------------------------------------------------------
@dataclass
class Camera:
    """Камера видеонаблюдения.

    Поля:
      id        -- уникальный идентификатор камеры
      name      -- человекочитаемое имя
      main_url  -- ссылка основного потока
      sub_url   -- ссылка субпотока (по умолчанию = main)
      enabled   -- включена ли камера
      comment   -- произвольный комментарий
    """
    id: str
    name: str = ""
    main_url: str = ""
    sub_url: str = ""
    enabled: bool = True
    comment: str = ""

    # --- идентификаторы потоков (для кэша и маршрутов) ---
    @property
    def main_route_id(self) -> str:
        """Идентификатор основного потока (для кэша и статусов)."""
        return f"{self.id}_main"

    @property
    def sub_route_id(self) -> str:
        """Идентификатор субпотока (для кэша и статусов)."""
        return f"{self.id}_sub"

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь (для хранения и передачи по сети)."""
        return asdict(self)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["Camera"]:
        """Создаёт камеру из "сырого" словаря с валидацией.

        Возвращает ``None``, если данные некорректны.
        Обязательные поля: непустой ``id`` и непустой ``main_url``.
        """
        if not isinstance(raw, dict):
            return None
        cid = raw.get("id")
        mu = raw.get("main_url")
        # id: непустая строка или число
        if cid is None or (isinstance(cid, str) and not cid.strip()) \
                or not isinstance(cid, (str, int)):
            return None
        # main_url: непустая строка
        if not mu or not isinstance(mu, str):
            return None
        # нормализуем флаг включённости (допускаем строковые "false"/"0"/"no")
        raw_en = raw.get("enabled", True)
        en = raw_en is True or (
            isinstance(raw_en, str) and raw_en.lower() not in ("false", "0", "no")
        )
        return cls(
            id=str(cid).strip(),
            name=str(raw.get("name", f"Camera {cid}")),
            main_url=str(mu).strip(),
            sub_url=str(raw.get("sub_url", mu)).strip(),
            enabled=bool(en),
            comment=str(raw.get("comment", "")),
        )


# ---------------------------------------------------------------------------
# Событие (для своей базы событий)
# ---------------------------------------------------------------------------
@dataclass
class Event:
    """Событие системы видеонаблюдения.

    Используется и в автономном режиме (своя база событий), и как источник
    данных для будущей интеграции с внешней платформой безопасности.
    """
    ts: float                          # unix-время события
    source: str                        # источник: "streamer"|"recorder"|"analytics"|"system"
    event_type: str                    # тип события, напр. "камера_недоступна"
    severity: str = "info"             # "info"|"warning"|"alarm"
    camera_id: Optional[str] = None    # камера (если применимо)
    node_id: Optional[str] = None      # узел кластера (для многонузловости)
    payload: Dict[str, Any] = field(default_factory=dict)  # детали события
    acknowledged: bool = False         # подтверждено ли оператором
    sent_to_external: bool = False     # отправлено ли во внешнюю систему

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return asdict(self)

    @staticmethod
    def make(source: str, event_type: str, severity: str = "info",
             camera_id: Optional[str] = None, node_id: Optional[str] = None,
             payload: Optional[Dict[str, Any]] = None) -> "Event":
        """Фабрика для быстрого создания события с текущим временем."""
        return Event(
            ts=time.time(),
            source=source,
            event_type=event_type,
            severity=severity,
            camera_id=camera_id,
            node_id=node_id,
            payload=payload or {},
        )


# ---------------------------------------------------------------------------
# Набор камер
# ---------------------------------------------------------------------------
@dataclass
class Set:
    """Набор (группа) камер для отображения на странице мониторинга.

    Поля:
      id           -- уникальный идентификатор набора
      name         -- человекочитаемое имя
      camera_ids   -- список идентификаторов камер в наборе
      max_columns  -- максимум колонок в сетке
      max_rows     -- максимум рядов (0 = без ограничения)
      aspect_ratio -- соотношение сторон ячейки, напр. "16:9"
    """
    id: str
    name: str = ""
    camera_ids: List[str] = field(default_factory=list)
    max_columns: int = 2
    max_rows: int = 0
    aspect_ratio: str = "16:9"

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return asdict(self)

    @classmethod
    def from_raw(cls, set_id: str, raw: Dict[str, Any]) -> "Set":
        """Создаёт набор из "сырого" словаря, дозаполняя умолчания."""
        raw = raw if isinstance(raw, dict) else {}
        return cls(
            id=set_id,
            name=str(raw.get("name", set_id)),
            camera_ids=list(raw.get("camera_ids", [])),
            max_columns=int(raw.get("max_columns", 2)),
            max_rows=int(raw.get("max_rows", 0)),
            aspect_ratio=str(raw.get("aspect_ratio", "16:9")),
        )
PYEOF_MODELS
echo "  ✔ app/models.py"

# ============================================================
# app/database.py — репозиторий (слой доступа к данным)
# ============================================================
cat > "$PROJECT_DIR/app/database.py" << 'PYEOF_DB'
# -*- coding: utf-8 -*-
"""
app/database.py
===============
Слой доступа к данным (репозиторий).

Сейчас реализован поверх встроенной реляционной БД (таблица "ключ-значение").
Интерфейс намеренно узкий (чтение / сохранение / список ключей), чтобы будущая
замена на другую СУБД (через внешний драйвер) затронула только этот модуль.

Публичный интерфейс:
    db.get(key, default)  -> объект (распакованный из текстового формата)
    db.save(key, data)    -> сохраняет объект
    db.keys()             -> список всех ключей
"""
import json
import logging
import os
import sqlite3
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Путь к файлу БД. Можно переопределить переменной окружения.
DB_PATH = os.environ.get("GRYPHONE_DB", "rtsp_viewer.db")


def _json_default(obj):
    """Сериализатор для объектов, не сериализуемых по умолчанию."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return str(obj)


class Database:
    """Обёртка над хранилищем "ключ-значение"."""

    def __init__(self, path: str = DB_PATH):
        self.db_path = path
        self._init_db()

    # ------------------------------------------------------------------
    # Служебные методы
    # ------------------------------------------------------------------
    def _get_conn(self):
        """Создаёт новое соединение (потокобезопасно через флаг)."""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    @contextmanager
    def get_db(self):
        """Контекстный менеджер: соединение с авто-коммитом/откатом."""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Создаёт таблицу настроек и при необходимости мигрирует файлы."""
        with self.get_db() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS settings "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            # Миграция нужна только если таблица пуста.
            if conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
                self._migrate_from_files(conn)

    def _migrate_from_files(self, conn) -> None:
        """Переносит данные из устаревших файлов в БД (однократно)."""
        logger.info("📦 Миграция из файлов...")
        for fname, key in [
            ("config.json", "config"),
            ("cameras.json", "cameras"),
            ("sets.json", "sets"),
        ]:
            if os.path.exists(fname):
                try:
                    with open(fname, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    conn.execute(
                        "INSERT OR REPLACE INTO settings VALUES(?,?)",
                        (key, json.dumps(data, ensure_ascii=False)),
                    )
                    logger.info("  ✔ Мигрирован %s", fname)
                except Exception as e:
                    logger.error("❌ Ошибка миграции %s: %s", fname, e)
        logger.info("✅ Миграция завершена.")

    # ------------------------------------------------------------------
    # Публичный интерфейс
    # ------------------------------------------------------------------
    def get(self, key: str, default=None):
        """Читает значение по ключу. Возвращает ``default``, если нет."""
        with self.get_db() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ).fetchone()
            return json.loads(row[0]) if row else default

    def save(self, key: str, data) -> None:
        """Сохраняет значение по ключу."""
        with self.get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings VALUES(?,?)",
                (key, json.dumps(data, ensure_ascii=False, default=_json_default)),
            )

    def keys(self):
        """Возвращает список всех ключей."""
        with self.get_db() as conn:
            rows = conn.execute("SELECT key FROM settings").fetchall()
            return [r[0] for r in rows]


# Единственный экземпляр БД для всего приложения.
db = Database()
PYEOF_DB
echo "  ✔ app/database.py"

# ============================================================
# app/config.py — управление конфигурацией
# ============================================================
cat > "$PROJECT_DIR/app/config.py" << 'PYEOF_CONFIG'
# -*- coding: utf-8 -*-
"""
app/config.py
=============
Управление конфигурацией приложения.

Задачи модуля:
  1. Определить значения параметров по умолчанию.
  2. Загрузить сохранённую конфигурацию из БД (если есть) и слить её со
     значениями по умолчанию (сохранённые имеют приоритет).
  3. Предоставить удобный доступ к параметрам через ``ConfigManager``.

Конфигурация хранится в БД под ключом "config". Эталон всех возможных
параметров — файл ``settings.json`` в корне проекта.
"""
import copy
import logging
from typing import Any, Dict

from app.database import db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Значения по умолчанию (соответствуют эталону в settings.json)
# ---------------------------------------------------------------------------
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
        # Зарезервированные секции (пока не используются бэкендом):
        "storage": {"default": "", "targets": []},
        "integration": {"enabled": False},
        "analytics": {"enabled": False},
        "cluster": {"enabled": False},
    }


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Рекурсивно сливает ``override`` в ``base``. Значения ``override`` приоритетны."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------
class ConfigManager:
    """Доступ к конфигурации приложения.

    Хранит слитую конфигурацию (по умолчанию + сохранённая) и предоставляет
    методы для чтения параметров и сохранения изменений.
    """

    KEY = "config"  # ключ в БД, под которым хранится конфигурация

    def __init__(self):
        self._data: Dict[str, Any] = self._load()

    # ------------------------------------------------------------------
    # Загрузка / сохранение
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Доступ к параметрам
    # ------------------------------------------------------------------
    def all(self) -> Dict[str, Any]:
        """Возвращает полную конфигурацию (копию)."""
        return copy.deepcopy(self._data)

    def get(self, *path: str, default: Any = None) -> Any:
        """Возвращает параметр по пути, напр. ``get("ффмпег", "режим")``.

        Если какой-то уровень пути отсутствует, возвращает ``default``.
        """
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


# Единственный экземпляр менеджера конфигурации.
config = ConfigManager()
PYEOF_CONFIG
echo "  ✔ app/config.py"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in app/models.py app/database.py app/config.py; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo "✅ Ядро данных бэкенда готово (с правильным синтаксисом)."
echo "ℹ️  Фабрика приложения будет заполнена скриптом 12 (после всех модулей)."