#!/bin/sh
# ============================================================================
# 67. update_scripts/67_move_config_to_sql.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Выносит эталонную конфигурацию из Python-кода (app/config.py) в SQL-файл
#   database/sql/config.sql. Конфиг становится внешним артефактом, который
#   легко редактировать, версионировать и распространять.
#
# АРХИТЕКТУРА:
#   1. Эталон живёт в database/sql/config.sql как INSERT в таблицу settings.
#   2. ConfigManager при первом запуске читает .sql, парсит JSON, удаляет
#      служебные ключи "_comment", сохраняет в БД под ключом "config".
#   3. При последующих запусках конфиг берётся из БД (пользовательские
#      изменения не теряются).
#   4. Резервный fallback — встроенный default_config() на случай, если
#      .sql файл недоступен.
#
# ИДЕМПОТЕНТНОСТЬ:
#   Повторный запуск безопасен. Если .sql файл и новый ConfigManager уже
#   на месте — изменения не дублируются.
#
# ЗАПУСК:
#   ./67_move_config_to_sql.sh
#
# ПОСЛЕ ЗАПУСКА:
#   Перезапустите сервер:  python main.py
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "67: Вынос эталонной конфигурации в database/sql/config.sql"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

# --- Детект Python ---
_detect_python() {
    for cmd in python python3 py; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" --version >/dev/null 2>&1; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}
PYTHON_CMD="$(_detect_python || true)"
if [ -z "$PYTHON_CMD" ]; then
    echo "ОШИБКА: не найден интерпретатор Python" >&2
    exit 1
fi
echo "Python: $PYTHON_CMD"

SQL_DIR="database/sql"
SQL_FILE="$SQL_DIR/config.sql"
CONFIG_PY="app/config.py"

# ============================================================================
# ШАГ 1: Резервные копии
# ============================================================================
echo ""
echo "--- ШАГ 1: Резервные копии ---"
if [ -f "$CONFIG_PY" ]; then
    cp "$CONFIG_PY" "$CONFIG_PY.bak-67"
    echo "  [BAK] $CONFIG_PY.bak-67"
fi
if [ -f "$SQL_FILE" ]; then
    cp "$SQL_FILE" "$SQL_FILE.bak-67"
    echo "  [BAK] $SQL_FILE.bak-67 (уже существовал)"
fi

# ============================================================================
# ШАГ 2: Создаём database/sql/config.sql с эталонным конфигом
# ============================================================================
echo ""
echo "--- ШАГ 2: Создание $SQL_FILE ---"

mkdir -p "$SQL_DIR"

"$PYTHON_CMD" - "$SQL_FILE" << 'PYEOF'
import sys
import json
from pathlib import Path

sql_file = Path(sys.argv[1])

# Эталонная конфигурация (точно как прислал пользователь)
default_config = {
  "_comment": "GRYPHONE — эталонная конфигурация со всеми возможными параметрами. Служебные ключи '_comment' игнорируются приложением. Секции с пометкой [ЗАРЕЗЕРВИРОВАНО] пока не читаются бэкендом и предназначены для будущих модулей.",

  "server": {
    "_comment": "Параметры веб-сервера: адрес и порт, на которых слушает бэкенд.",
    "host": "0.0.0.0",
    "port": 5000
  },

  "paths": {
    "_comment": "Пути к данным: файл БД камер, файл БД наборов, каталог кэша HLS-сегментов.",
    "cameras_db": "rtsp_viewer.db",
    "sets_db": "rtsp_viewer.db",
    "hls_cache": "hls_cache"
  },

  "ffmpeg": {
    "_comment": "Настройки FFmpeg: режим обработки, логирование, глобальные параметры захвата и HLS, транскодирование.",
    "mode": "auto",
    "logging": {
      "_comment": "Уровень и формат логов, период вывода статистики в лог.",
      "level": "info",
      "stats_period": 1,
      "hide_banner": True,
      "generate_report": False
    },
    "global": {
      "_comment": "Глобальные параметры захвата и генерации HLS.",
      "transport": "tcp",
      "buffer_mode": "nobuffer",
      "error_detection": "ignore_err",
      "threads": 0,
      "probe_timeout": 3,
      "probe_analyze_duration": 1000000,
      "probe_size": 1000000,
      "hls_time": 2,
      "hls_list_size": 4,
      "hls_flags": "delete_segments+temp_file+program_date_time"
    },
    "copy": {
      "_comment": "Режим прямого копирования потока без перекодирования.",
      "note": "Прямой поток"
    },
    "transcode": {
      "_comment": "Параметры транскодирования (когда поток перекодируется).",
      "gpu_encoder": "auto",
      "video_bitrate": "2500k",
      "video_maxrate": "4000k",
      "video_bufsize": "8000k",
      "gop_size": 30,
      "keyint_min": 30,
      "audio_bitrate": "48k",
      "pix_fmt": "yuv420p",
      "preset": "ultrafast",
      "tune": "zerolatency"
    }
  },

  "app": {
    "_comment": "Параметры приложения: задержки перезапуска воркеров, пороги стабильности и отката с GPU, минимальный размер отдаваемого файла, набор по умолчанию.",
    "backoff_max": 30,
    "stable_runtime_threshold": 60,
    "gpu_fallback_threshold": 5.0,
    "cleanup_min_file_size": 512,
    "default_set": ""
  },

  "cleanup": {
    "_comment": "Автоочистка кэша HLS-сегментов.",
    "enabled": True,
    "interval_seconds": 300,
    "max_age_hours": 24
  },

  "performance": {
    "_comment": "Производительность: число потоков для зондирования камер, период рассылки статусов по SSE.",
    "probe_workers": 32,
    "sse_interval": 1.0
  },

  "events": {
    "_comment": "Своя база событий (нужна и в автономном режиме, и для будущей интеграции с PSIM). Таблица 'events': ts, source, camera_id, node_id, event_type, severity, payload, acknowledged, sent_to_psim.",
    "enabled": True,
    "retention_days": 30,
    "db_path": "rtsp_viewer.db"
  },

  "storage": {
    "_comment": "[ЗАРЕЗЕРВИРОВАНО] Запись на сетевые хранилища (сетевые NAS по NFS и другим протоколам). Текущая версия бэкенда эту секцию ещё не читает. План: монтирование дисков на уровне ОС + StorageManager с выбором активного хранилища по приоритету и свободному месту.",
    "default": "nas-primary",
    "targets": [
      {
        "id": "nas-primary",
        "type": "nfs",
        "address": "192.168.1.100:/export/video",
        "mount_point": "/mnt/video-primary",
        "enabled": True,
        "priority": 1,
        "retention_days": 30,
        "min_free_gb": 100
      },
      {
        "id": "local-buffer",
        "type": "local",
        "address": "",
        "mount_point": "/var/video-buffer",
        "enabled": True,
        "priority": 99,
        "retention_days": 3,
        "min_free_gb": 20
      }
    ]
  },

  "integration": {
    "_comment": "[ЗАРЕЗЕРВИРОВАНО] Интеграция с большой системой (будущий аналог/адаптер для внешней платформы безопасности). Владелец конфигурации камер — сам GRYPHONE, синхронизация однонаправленная: отсюда наружу. Текущая версия бэкенда эту секцию ещё не читает.",
    "enabled": False,
    "mode": "standalone",
    "external_api_url": "http://core.local:8080",
    "events_bus": {
      "_comment": "Шина событий для публикации событий наружу.",
      "type": "none",
      "url": "nats://nats:4222",
      "subject_prefix": "gryphone.events.video"
    },
    "config_sync": {
      "_comment": "Синхронизация конфигурации камер наружу (владелец — этот проект).",
      "enabled": False,
      "direction": "out",
      "interval_seconds": 60
    },
    "auth": {
      "_comment": "Режим аутентификации: своя или делегированная внешней системе.",
      "mode": "local"
    }
  },

  "analytics": {
    "_comment": "[ЗАРЕЗЕРВИРОВАНО] Видеоаналитика: декодирование на GPU и инференс моделей. Текущая версия бэкенда эту секцию ещё не читает. План: декодирование на GPU (аппаратно), передача кадров на инференс-сервер, детекция объектов/движения.",
    "enabled": False,
    "gpu": {
      "_comment": "Параметры GPU: устройство и бэкенд аппаратного декодирования.",
      "device": 0,
      "decode_backend": "auto"
    },
    "inference": {
      "_comment": "Инференс-сервер моделей и список моделей.",
      "url": "http://localhost:8000",
      "models": []
    },
    "detection": {
      "_comment": "Что детектировать.",
      "enabled": False,
      "types": []
    }
  },

  "cluster": {
    "_comment": "[ЗАРЕЗЕРВИРОВАНО] Многонузловость: работа на нескольких узлах/кластере. Текущая версия бэкенда эту секцию ещё не читает. План: оркестрация, обнаружение узлов, балансировка камер по узлам.",
    "enabled": False,
    "node_id": "",
    "discovery": {
      "type": "none",
      "endpoints": []
    }
  }
}

# Сериализуем JSON с красивым форматированием
json_text = json.dumps(default_config, ensure_ascii=False, indent=2)
# Экранируем одинарные кавычки для SQL (одинарные кавычки удваиваются в SQL)
json_escaped = json_text.replace("'", "''")

sql_content = f'''-- ============================================================================
-- GRYPHONE — эталонная конфигурация по умолчанию
-- ----------------------------------------------------------------------------
-- Этот файл содержит INSERT-команду, которая загружает конфигурацию в таблицу
-- `settings` SQLite-базы данных. При первом запуске ConfigManager прочитает
-- этот файл, извлечёт JSON и запишет его под ключом 'config'.
--
-- Ключи "_comment" являются служебными и игнорируются приложением.
-- Секции с пометкой [ЗАРЕЗЕРВИРОВАНО] пока не читаются бэкендом.
--
-- Для редактирования конфига:
--   1. Отредактируйте JSON ниже
--   2. Удалите ключ 'config' из таблицы settings (или удалите .db файл)
--   3. Перезапустите сервер
-- ============================================================================

INSERT OR REPLACE INTO settings (key, value) VALUES ('config', '{json_escaped}');
'''

sql_file.write_text(sql_content, encoding="utf-8")
print(f"  [OK] Создан {sql_file} ({len(sql_content)} байт)")
PYEOF

# ============================================================================
# ШАГ 3: Перезаписываем app/config.py — загрузка из .sql вместо default_config()
# ============================================================================
echo ""
echo "--- ШАГ 3: Перезапись $CONFIG_PY ---"

cat > "$CONFIG_PY" << 'CONFIGPY'
# -*- coding: utf-8 -*-
"""
app/config.py
=============

Управление конфигурацией приложения.

ИСТОЧНИК ЭТАЛОНА:  database/sql/config.sql
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
DEFAULT_SQL_PATH = BASE_DIR / "database" / "sql" / "config.sql"

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

    Используется только если database/sql/config.sql не найден или битый.
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
        2. Эталон из database/sql/config.sql.
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
CONFIGPY

echo "  [OK] $CONFIG_PY перезаписан"

# ============================================================================
# ШАГ 4: Проверка
# ============================================================================
echo ""
echo "--- ШАГ 4: Проверка ---"

"$PYTHON_CMD" << 'PYEOF'
import sys
try:
    # Принудительно перезагружаем модуль, чтобы использовать новую версию
    import importlib
    if 'app.config' in sys.modules:
        del sys.modules['app.config']

    from app.config import config

    # Проверяем базовые секции
    sections = ["server", "paths", "ffmpeg", "app", "cleanup",
                "performance", "events", "storage", "integration",
                "analytics", "cluster"]

    missing = [s for s in sections if s not in config.all()]
    if missing:
        print(f"  [WARN] Отсутствуют секции: {missing}")
    else:
        print(f"  [OK] Все {len(sections)} секций конфигурации на месте")

    # Проверяем, что _comment удалены
    import json
    raw = json.dumps(config.all())
    if '"_comment"' in raw:
        print("  [FAIL] Служебные ключи '_comment' не были удалены")
        sys.exit(1)
    else:
        print("  [OK] Служебные ключи '_comment' успешно удалены")

    # Проверяем чтение по пути
    host = config.get("server", "host", default=None)
    port = config.get("server", "port", default=None)
    print(f"  [OK] server.host={host}, server.port={port}")

    # Проверяем зарезервированные секции
    for section in ["storage", "integration", "analytics", "cluster"]:
        if section in config.all():
            print(f"  [OK] Зарезервированная секция '{section}' загружена")

    print("")
    print("Конфигурация успешно загружена из database/sql/config.sql")

except Exception as e:
    print(f"  [FAIL] Ошибка при проверке: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

echo ""
echo "============================================================================"
echo "Готово."
echo ""
echo "Файлы:"
echo "  $SQL_FILE         — эталонная конфигурация (редактируется пользователем)"
echo "  $CONFIG_PY        — обновлён, читает из SQL"
echo "  $CONFIG_PY.bak-67 — резервная копия старого config.py"
echo ""
echo "Как редактировать конфиг:"
echo "  1. Откройте $SQL_FILE"
echo "  2. Измените JSON внутри INSERT-команды"
echo "  3. Удалите ключ 'config' из БД или удалите database/*.db"
echo "  4. Перезапустите сервер:  python main.py"
echo ""
echo "Или через API (не требует перезапуска SQL):"
echo "  POST /api/config/save с новым JSON"
echo "============================================================================"