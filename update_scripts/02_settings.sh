#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 02: НАСТРОЙКИ
#  ------------------------------------------------------------
#  Создаёт:
#    - settings.json — эталонная конфигурация со ВСЕМИ возможными
#      параметрами:
#        • текущие РАБОЧИЕ параметры (просмотрщик/стример);
#        • ЗАРЕЗЕРВИРОВАННЫЕ параметры под будущие модули
#          (запись на сетевые NAS, интеграция с PSIM,
#          видеоаналитика на GPU/Triton, кластер, база событий).
#    - если файла "config.json" ещё нет, копирует его из
#      "settings.json" (приложение при первом запуске читает
#      именно "config.json" и мигрирует его в БД).
#
#  Примечание: формат JSON не поддерживает комментарии, поэтому
#  документация встроена через служебные ключи "_comment".
#  Приложение их игнорирует — они не влияют на логику.
#
#  Запуск:   bash 02_settings.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ------------------------------------------------------------
# settings.json — полная конфигурация со всеми параметрами
# ------------------------------------------------------------
cat > "$PROJECT_DIR/settings.json" << 'JSONEOF'
{
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
      "hide_banner": true,
      "generate_report": false
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
    "enabled": true,
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
    "enabled": true,
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
        "enabled": true,
        "priority": 1,
        "retention_days": 30,
        "min_free_gb": 100
      },
      {
        "id": "local-buffer",
        "type": "local",
        "address": "",
        "mount_point": "/var/video-buffer",
        "enabled": true,
        "priority": 99,
        "retention_days": 3,
        "min_free_gb": 20
      }
    ]
  },

  "integration": {
    "_comment": "[ЗАРЕЗЕРВИРОВАНО] Интеграция с большой системой (будущий аналог/адаптер для внешней платформы безопасности). Владелец конфигурации камер — сам GRYPHONE, синхронизация однонаправленная: отсюда наружу. Текущая версия бэкенда эту секцию ещё не читает.",
    "enabled": false,
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
      "enabled": false,
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
    "enabled": false,
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
      "enabled": false,
      "types": []
    }
  },

  "cluster": {
    "_comment": "[ЗАРЕЗЕРВИРОВАНО] Многонузловость: работа на нескольких узлах/кластере. Текущая версия бэкенда эту секцию ещё не читает. План: оркестрация, обнаружение узлов, балансировка камер по узлам.",
    "enabled": false,
    "node_id": "",
    "discovery": {
      "type": "none",
      "endpoints": []
    }
  }
}
JSONEOF
echo "  ✔ settings.json"

# ------------------------------------------------------------
# Копируем settings.json в config.json, если последнего ещё нет.
# Приложение при первом запуске читает именно "config.json".
# ------------------------------------------------------------
if [ ! -f "$PROJECT_DIR/config.json" ]; then
  cp "$PROJECT_DIR/settings.json" "$PROJECT_DIR/config.json"
  echo "  ✔ Создан config.json (копия settings.json)"
else
  echo "  ⏭ config.json уже существует — не перезаписываю"
fi

echo "✅ Файлы конфигурации готовы."
echo "ℹ️  Зарезервированные секции (запись на сетевые диски, интеграция,"
echo "    аналитика, кластер) пока не читаются бэкендом — это задел на будущее."