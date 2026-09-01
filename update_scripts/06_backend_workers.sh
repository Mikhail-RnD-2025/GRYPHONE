#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 06: ВОРКЕРЫ
#  ------------------------------------------------------------
#  Заполняет фоновые задачи:
#    - app/workers/__init__.py        — маркер пакета
#    - app/workers/hls_worker.py      — захват потока (полная реализация,
#                                       использует исправленную проверку хоста)
#    - app/workers/cleanup_worker.py  — фоновая очистка кэша сегментов
#
#  Запуск:   bash 06_backend_workers.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# app/workers/__init__.py — маркер пакета
# ============================================================
cat > "$PROJECT_DIR/app/workers/__init__.py" << 'PYEOF_INIT'
# -*- coding: utf-8 -*-
"""
Пакет фоновых задач (воркеров) приложения.

Воркеры:
  - hls_worker     : захват одного потока (проверка хоста, запуск
                     конвертера, генерация сегментов, статусы)
  - cleanup_worker : фоновая очистка кэша сегментов
"""
PYEOF_INIT
echo "  ✔ app/workers/__init__.py"

# ============================================================
# app/workers/hls_worker.py — захват потока
# ============================================================
cat > "$PROJECT_DIR/app/workers/hls_worker.py" << 'PYEOF_HLS'
# -*- coding: utf-8 -*-
"""
app/workers/hls_worker.py
=========================
Воркер захвата одного потока камеры.

Цикл работы воркера:
  1. Проверяет доступность камеры (быстрая проверка хоста с таймаутом).
  2. Зондирует камеру, чтобы определить кодек и выбрать режим
     (копирование без перекодирования или перекодирование).
  3. Запускает внешний конвертер для генерации сегментов.
  4. Читает логи процесса, извлекает метрики и обновляет статус потока.
  5. При сбое ждёт с экспоненциально растущей задержкой и повторяет.

Использует утилиты из ``app.utils.ffmpeg`` и менеджер стримера для
обновления статусов и логов.
"""
import asyncio
import logging
import re
import subprocess
import time

from app.config import config
from app.services.camera_service import camera_service
from app.utils.ffmpeg import (
    build_ffmpeg_cmd,
    check_host,
    decide_stream_mode,
    ffmpeg_path,
    probe_camera,
)

logger = logging.getLogger(__name__)

# Регулярное выражение для извлечения метрик из строк статистики конвертера.
# Пример строки: "кадр=123 к/с=25.0 ... время=00:00:05.00 битрейт=2500кбит/с"
_STATS_RE = re.compile(
    r"frame=\s*(\d+)\s*fps=\s*([\d.]+)\s*q=\s*([\d.-]+)\s*"
    r"size=\s*([\d.]+[a-zA-Z]+)\s*time=(\S+)\s*bitrate=([\d.]+[a-zA-Z/]+)"
)


async def hls_worker(url: str, route_id: str, cam_id: str, manager) -> None:
    """Воркер захвата одного потока.

    Аргументы:
      url      -- ссылка на поток камеры;
      route_id -- идентификатор потока (напр. "ид_камеры_основной");
      cam_id   -- идентификатор камеры;
      manager  -- менеджер стримера (для статусов и логов).
    """
    cfg = config.all()
    hls_cache = cfg.get("пути", {}).get("кэш_hls", "hls_cache")
    ff_cfg = cfg.get("ffmpeg", {})
    global_cfg = ff_cfg.get("глобальные", {})
    app_cfg = cfg.get("приложение", {})

    backoff = 1  # текущая задержка повторного запуска (экспоненциальный рост)
    backoff_max = app_cfg.get("макс_задержка", 30)

    logger.info("🔍 Воркер запущен: %s", route_id)
    try:
        while True:
            # --- проверяем, включена ли ещё камера ---
            cam = camera_service.get_camera(cam_id)
            if not cam or not cam.enabled:
                logger.info("⏹ Камера отключена, воркер завершается: %s", route_id)
                break

            manager.set_status(route_id, "подключение", "Подключение...")

            # --- быстрая проверка доступности хоста (с таймаутом) ---
            probe_timeout = global_cfg.get("таймаут_зондирования", 3)
            if not await check_host(url, timeout=probe_timeout):
                manager.set_status(route_id, "недоступна", "Хост недоступен")
                logger.warning("⚠️ Хост недоступен: %s", route_id)
                await asyncio.sleep(min(backoff * 2, 15))
                backoff = min(backoff * 2, 15)
                continue

            # --- хост доступен, сбрасываем задержку ---
            backoff = 1
            manager.clear_log(route_id)

            # --- зондируем камеру для выбора режима ---
            try:
                loop = asyncio.get_running_loop()
                codec, profile, pix_fmt = await loop.run_in_executor(
                    None, probe_camera, url, global_cfg
                )
            except Exception:
                codec, profile, pix_fmt = "неизвестно", "неизвестно", "неизвестно"

            mode_cfg = ff_cfg.get("режим", "авто")
            if mode_cfg == "копия":
                mode = "копия"
            elif mode_cfg == "перекодирование":
                mode = "перекодирование"
            else:
                mode = decide_stream_mode(codec, profile, pix_fmt)
            logger.info("✅ %s: режим=%s (кодек=%s)", route_id, mode, codec)

            # --- внутренний цикл запуска конвертера ---
            while True:
                cam = camera_service.get_camera(cam_id)
                if not cam or not cam.enabled:
                    break
                manager.set_status(route_id, "подключение", "Запуск потока...")

                cmd = build_ffmpeg_cmd(url, route_id, mode, ff_cfg, hls_cache)
                started_at = time.time()
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                    )

                    # Асинхронное чтение логов процесса.
                    async def _read_logs():
                        buf = b""
                        try:
                            async for chunk in proc.stderr:
                                buf += chunk
                                while b"\n" in buf or b"\r" in buf:
                                    sep = b"\r" if b"\r" in buf else b"\n"
                                    line, buf = buf.split(sep, 1)
                                    if not line.strip():
                                        continue
                                    text = line.decode("utf-8", "ignore").strip()
                                    manager.add_log(
                                        route_id,
                                        f"[{time.strftime('%H:%M:%S')}] {text}",
                                    )
                                    # Извлекаем метрики из строк статистики.
                                    m = _STATS_RE.search(text)
                                    if m:
                                        manager.set_status(
                                            route_id, "в_сети", "Поток активен",
                                            metrics={
                                                "к/с": m.group(2),
                                                "битрейт": m.group(6),
                                                "время": m.group(5),
                                            },
                                        )
                        except Exception:
                            pass

                    log_task = asyncio.create_task(_read_logs())
                    return_code = await proc.wait()
                    log_task.cancel()
                    success = (return_code == 0)
                except Exception as e:
                    success = False
                    return_code = -1
                    logger.error("Ошибка конвертера для %s: %s", route_id, e)

                # --- обрабатываем результат ---
                if success:
                    manager.set_status(route_id, "в_сети", "Поток активен")
                    backoff = 1
                else:
                    manager.set_status(route_id, "недоступна", f"Ошибка: {return_code}")
                    backoff = min(backoff * 2, backoff_max)
                    logger.warning(
                        "⚠️ Поток завершился с ошибкой %s для %s, повтор через %s с",
                        return_code, route_id, backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue
                # Успешный запуск: продолжаем следить (конвертер работает).
                break
    except asyncio.CancelledError:
        logger.info("⏹ Воркер отменён: %s", route_id)
    finally:
        # Освобождаем ресурсы в менеджере стримера.
        manager.cleanup(route_id)
        logger.info("🧹 Воркер завершён: %s", route_id)
PYEOF_HLS
echo "  ✔ app/workers/hls_worker.py"

# ============================================================
# app/workers/cleanup_worker.py — фоновая очистка кэша
# ============================================================
cat > "$PROJECT_DIR/app/workers/cleanup_worker.py" << 'PYEOF_CLEAN'
# -*- coding: utf-8 -*-
"""
app/workers/cleanup_worker.py
=============================
Фоновая задача очистки кэша сегментов.

Периодически проходит по каталогу кэша и удаляет старые сегменты
(файлы ``.ts``), возраст которых превышает заданный порог. Также удаляет
опустевшие подкаталоги камер. Запускается в отдельном потоке.

Параметры берутся из конфигурации (секция "очистка").
"""
import logging
import time
from pathlib import Path

from app.config import config

logger = logging.getLogger(__name__)


def cleanup_worker() -> None:
    """Бесконечный цикл очистки кэша сегментов.

    Запускается в отдельном потоке при старте приложения.
    """
    while True:
        try:
            cfg = config.all()
            clean_cfg = cfg.get("очистка", {})
            # Если очистка отключена — просто ждём и проверяем снова.
            if not clean_cfg.get("включена", True):
                time.sleep(60)
                continue

            hls_cache = cfg.get("пути", {}).get("кэш_hls", "hls_cache")
            cache_dir = Path(hls_cache)
            if not cache_dir.is_dir():
                time.sleep(300)
                continue

            now = time.time()
            max_age_sec = clean_cfg.get("макс_возраст_часов", 24) * 3600

            # Проходим по подкаталогам камер.
            for cam_dir in cache_dir.iterdir():
                if not cam_dir.is_dir():
                    continue
                # Проходим по подкаталогам потоков внутри камеры.
                for stream_dir in cam_dir.iterdir():
                    if not stream_dir.is_dir():
                        continue
                    # Удаляем старые сегменты.
                    for f in stream_dir.iterdir():
                        if f.suffix == ".ts" and (now - f.stat().st_mtime) > max_age_sec:
                            try:
                                f.unlink()
                            except OSError:
                                pass
                    # Удаляем опустевший подкаталог потока.
                    try:
                        if not any(stream_dir.iterdir()):
                            stream_dir.rmdir()
                    except OSError:
                        pass
        except Exception as e:
            logger.warning("Ошибка очистки кэша: %s", e)

        # Ждём до следующей итерации.
        interval = config.get("очистка", "интервал_секунд", default=300)
        time.sleep(interval)
PYEOF_CLEAN
echo "  ✔ app/workers/cleanup_worker.py"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in app/workers/__init__.py app/workers/hls_worker.py app/workers/cleanup_worker.py; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo "✅ Воркеры готовы (с правильным синтаксисом)."
echo "ℹ️  Утилиты конвертера (включая исправленную проверку хоста) — скрипт 07."