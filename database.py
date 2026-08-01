#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
database.py
Простое JSON-based хранилище для конфигурации, камер и наборов.
Все методы асинхронные для совместимости с Quart/Hypercorn.
"""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Папка для хранения данных
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


class DBManager:
    """Менеджер базы данных на основе JSON-файлов."""

    def __init__(self):
        """Инициализация менеджера БД."""
        self._lock = asyncio.Lock()
        logger.info(f"📁 DBManager инициализирован. Папка данных: {DATA_DIR.resolve()}")

    async def init(self):
        """Асинхронная инициализация (создание структуры, если нужно)."""
        # Для JSON-based хранилища инициализация не требуется
        # Но метод нужен для совместимости с main.py
        logger.info("✅ DBManager.init() выполнен успешно")

    def _get_file_path(self, key: str) -> Path:
        """Получение пути к файлу для данного ключа."""
        return DATA_DIR / f"{key}.json"

    async def load(self, key: str) -> Optional[Any]:
        """Загрузка данных из JSON-файла."""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            logger.debug(f"📭 Файл {file_path.name} не найден, возвращаем None")
            return None

        try:
            async with self._lock:
                # Используем to_thread для неблокирующего чтения
                data = await asyncio.to_thread(self._read_json, file_path)
                logger.debug(f"📥 Загружено из {file_path.name}: {type(data).__name__}")
                return data
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {file_path.name}: {e}")
            return None

    async def save(self, key: str, data: Any) -> bool:
        """Сохранение данных в JSON-файл."""
        file_path = self._get_file_path(key)

        try:
            async with self._lock:
                # Используем to_thread для неблокирующей записи
                await asyncio.to_thread(self._write_json, file_path, data)
                logger.debug(f"📤 Сохранено в {file_path.name}")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения {file_path.name}: {e}")
            return False

    async def get_archive_stats(self) -> Dict[str, Any]:
        """Получение статистики архива (используется в settings)."""
        try:
            # Подсчет файлов в папке архива
            archive_dir = Path("archive")
            if not archive_dir.exists():
                return {
                    "total_files": 0,
                    "total_size": 0,
                    "total_size_human": "0 B",
                    "pools": []
                }

            total_files = 0
            total_size = 0

            for f in archive_dir.rglob("*"):
                if f.is_file():
                    total_files += 1
                    total_size += f.stat().st_size

            # Форматирование размера
            if total_size == 0:
                size_human = "0 B"
            else:
                units = ['B', 'KB', 'MB', 'GB', 'TB']
                unit_index = 0
                size = float(total_size)
                while size >= 1024 and unit_index < len(units) - 1:
                    size /= 1024
                    unit_index += 1
                size_human = f"{size:.2f} {units[unit_index]}"

            return {
                "total_files": total_files,
                "total_size": total_size,
                "total_size_human": size_human,
                "pools": []  # Можно расширить для поддержки пулов
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики архива: {e}")
            return {
                "total_files": 0,
                "total_size": 0,
                "total_size_human": "0 B",
                "pools": []
            }

    @staticmethod
    def _read_json(file_path: Path) -> Any:
        """Синхронное чтение JSON (вызывается через to_thread)."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def _write_json(file_path: Path, data: Any):
        """Синхронная запись JSON (вызывается через to_thread)."""
        # Записываем во временный файл, затем переименовываем (атомарная операция)
        temp_path = file_path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Атомарная замена файла
        if os.name == 'nt':
            # На Windows нужно сначала удалить целевой файл
            if file_path.exists():
                file_path.unlink()
        temp_path.rename(file_path)


# Глобальный экземпляр для использования в других модулях
# (опционально, можно создавать локально где нужно)
db = DBManager()