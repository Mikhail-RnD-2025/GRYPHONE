#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive.py
Фоновый воркер для архивации HLS-сегментов в постоянное хранилище.
Автоматически копирует готовые сегменты из HLS-кэша в папку архива,
организуя их по камерам и датам.
"""
import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path

from state import CFG, CAMERAS_DB

logger = logging.getLogger(__name__)


async def archive_worker_async():
    """
    Основной асинхронный цикл архивации.
    Запускается как фоновая задача при старте сервера.
    """
    logger.info("📼 Archive worker started (Async)")

    # Интервал проверки (в секундах)
    check_interval = CFG.get("archive", {}).get("check_interval", 10)

    while True:
        try:
            await _process_archive()
            await asyncio.sleep(check_interval)
        except asyncio.CancelledError:
            logger.info("🛑 Archive worker cancelled")
            break
        except Exception as e:
            logger.error(f"❌ Archive worker error: {e}", exc_info=True)
            await asyncio.sleep(check_interval)


async def _process_archive():
    """Обработка архивации для всех активных камер."""
    hls_cache_root = Path(CFG.get("paths", {}).get("hls_cache", "hls_cache"))
    archive_root = Path(CFG.get("archive", {}).get("root", "archive"))

    if not hls_cache_root.exists():
        return

    # Создаем корневую папку архива, если её нет
    archive_root.mkdir(parents=True, exist_ok=True)

    # Проходим по всем камерам
    for cam_id, cam_data in CAMERAS_DB.items():
        if not cam_data.get("enabled", True):
            continue

        # Проверяем, включена ли архивация для этой камеры
        if not cam_data.get("archive_enabled", False):
            continue

        cam_hls_dir = hls_cache_root / "camera" / f"{cam_id}_main"
        if not cam_hls_dir.exists():
            continue

        # Создаем папку архива для камеры (организуем по датам)
        today = datetime.now().strftime("%Y-%m-%d")
        cam_archive_dir = archive_root / cam_id / today
        cam_archive_dir.mkdir(parents=True, exist_ok=True)

        # Копируем готовые сегменты
        copied_count = 0
        for segment_file in cam_hls_dir.glob("seg_*.m4s"):
            try:
                # Проверяем, что сегмент полностью записан (не .tmp)
                if segment_file.suffix == ".m4s" and segment_file.stat().st_size > 0:
                    dest_file = cam_archive_dir / segment_file.name

                    # Если файл уже есть в архиве, пропускаем
                    if dest_file.exists():
                        continue

                    # Копируем файл (используем to_thread для неблокирующей операции)
                    await asyncio.to_thread(
                        shutil.copy2,
                        str(segment_file),
                        str(dest_file)
                    )
                    copied_count += 1

                    # Логируем только первые несколько файлов, чтобы не засорять логи
                    if copied_count <= 3:
                        logger.debug(f"📼 Архивирован: {cam_id} -> {dest_file.name}")

            except Exception as e:
                logger.warning(f"⚠️ Не удалось архивировать {segment_file.name}: {e}")

        if copied_count > 3:
            logger.info(f"📼 Архивировано {copied_count} сегментов для камеры {cam_id}")


# Для совместимости с кодом, который может вызывать функцию напрямую
async def start_archive():
    """Альтернативное имя для запуска архивации."""
    await archive_worker_async()