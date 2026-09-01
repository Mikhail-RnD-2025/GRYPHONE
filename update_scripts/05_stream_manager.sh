#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 05: МЕНЕДЖЕР СТРИМЕРА
#  ------------------------------------------------------------
#  Заполняет:
#    - app/services/stream_manager.py — сердце стримера:
#        • асинхронный цикл событий в отдельном потоке;
#        • синхронизация воркеров со списком камер;
#        • хранение и предоставление статусов потоков;
#        • хранение и предоставление логов потоков.
#
#  Запуск:   bash 05_stream_manager.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# app/services/stream_manager.py — сердце стримера
# ============================================================
cat > "$PROJECT_DIR/app/services/stream_manager.py" << 'PYEOF_SM'
# -*- coding: utf-8 -*-
"""
app/services/stream_manager.py
==============================
Сервис управления асинхронными воркерами захвата потоков и их статусами.

Это «сердце стримера». Отвечает за:
  - запуск асинхронного цикла событий в отдельном потоке;
  - синхронизацию воркеров со списком камер (запуск / остановка);
  - хранение и предоставление статусов потоков;
  - хранение и предоставление логов потоков.

Использует воркер захвата из ``app.workers.hls_worker``. Модели камер
берутся из ``app.models``.
"""
import asyncio
import logging
import threading
from collections import deque
from typing import Dict, List, Optional

from app.models import Camera

logger = logging.getLogger(__name__)


class StreamManager:
    """Управление воркерами захвата и статусами потоков."""

    def __init__(self):
        # Асинхронный цикл событий и поток, в котором он работает.
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

        # Активные задачи-воркеры: {идентификатор_потока: задача}.
        self._tasks: Dict[str, asyncio.Task] = {}
        # Статусы потоков: {идентификатор_потока: {статус, сообщение, метрики}}.
        self._stats: Dict[str, dict] = {}
        # Логи потоков: {идентификатор_потока: очередь строк}.
        self._logs: Dict[str, deque] = {}

        # Блокировки для потокобезопасного доступа.
        self._lock = threading.RLock()      # защищает задачи и статусы
        self._log_lock = threading.Lock()   # защищает логи

        self._started = False

    # ------------------------------------------------------------------
    # Запуск / остановка асинхронного цикла
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Запускает асинхронный цикл событий в отдельном потоке."""
        if self._started:
            return
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="StreamManagerLoop"
        )
        self._thread.start()
        self._started = True
        logger.info("⚡ Асинхронный цикл стримера запущен")

    def _run_loop(self) -> None:
        """Точка входа для потока с циклом событий."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def stop(self) -> None:
        """Останавливает все воркеры и цикл событий."""
        if not self._started or self._loop is None:
            return
        # Отменяем все активные задачи-воркеры.
        for task in list(self._tasks.values()):
            self._loop.call_soon_threadsafe(task.cancel)
        self._tasks.clear()
        # Останавливаем цикл событий.
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._started = False
        logger.info("⏹ Асинхронный цикл стримера остановлен")

    # ------------------------------------------------------------------
    # Синхронизация воркеров с камерами
    # ------------------------------------------------------------------
    def sync(self, cameras: List[Camera]) -> None:
        """Синхронизирует воркеры со списком камер (запускает/останавливает).

        Вызывается при изменении списка камер: добавление, удаление,
        включение/выключение. Планирует асинхронную синхронизацию в цикле.
        """
        if not self._started or self._loop is None:
            logger.warning("⚠️ Стример не запущен, синхронизация отложена")
            return
        asyncio.run_coroutine_threadsafe(self._sync(cameras), self._loop)

    async def _sync(self, cameras: List[Camera]) -> None:
        """Асинхронная синхронизация воркеров (выполняется в цикле событий)."""
        # Отложенный импорт, чтобы избежать циклической зависимости.
        from app.workers.hls_worker import hls_worker

        # Собираем потоки, которые должны работать: {ид_потока: (ссылка, ид_камеры)}.
        needed: Dict[str, tuple] = {}
        for cam in cameras:
            if not cam.enabled:
                continue
            needed[cam.main_route_id] = (cam.main_url, cam.id)
            # Субпоток — только если он отличается от основного.
            if cam.sub_url and cam.sub_url != cam.main_url:
                needed[cam.sub_route_id] = (cam.sub_url, cam.id)

        with self._lock:
            # Останавливаем воркеры, которые больше не нужны.
            for rid in list(self._tasks.keys()):
                if rid not in needed:
                    task = self._tasks.pop(rid)
                    task.cancel()
                    self._stats.pop(rid, None)
                    logger.info("⏹ Остановлен воркер: %s", rid)
            # Запускаем воркеры для новых потоков.
            for rid, (url, cam_id) in needed.items():
                if rid not in self._tasks:
                    task = self._loop.create_task(
                        hls_worker(url, rid, cam_id, self)
                    )
                    self._tasks[rid] = task
                    logger.info("🚀 Запущен воркер: %s", rid)

    # ------------------------------------------------------------------
    # Статусы потоков
    # ------------------------------------------------------------------
    def set_status(self, route_id: str, state: str, msg: str = "",
                   metrics: Optional[dict] = None) -> None:
        """Устанавливает статус потока.

        ``state`` — одно из: "подключение" | "в_сети" | "недоступна".
        """
        with self._lock:
            self._stats[route_id] = {
                "state": state,
                "msg": msg,
                "metrics": metrics or {},
            }

    def get_all_stats(self) -> Dict[str, dict]:
        """Возвращает статусы всех потоков (копию словаря)."""
        with self._lock:
            return dict(self._stats)

    def get_status(self, route_id: str) -> Optional[dict]:
        """Возвращает статус одного потока или ``None``."""
        with self._lock:
            return self._stats.get(route_id)

    # ------------------------------------------------------------------
    # Логи потоков
    # ------------------------------------------------------------------
    def add_log(self, route_id: str, line: str, maxlen: int = 500) -> None:
        """Добавляет строку в лог потока (с ограничением длины очереди)."""
        with self._log_lock:
            if route_id not in self._logs:
                self._logs[route_id] = deque(maxlen=maxlen)
            self._logs[route_id].append(line)

    def clear_log(self, route_id: str) -> None:
        """Очищает лог потока."""
        with self._log_lock:
            if route_id in self._logs:
                self._logs[route_id].clear()

    def get_logs(self, limit: int = 100) -> Dict[str, List[str]]:
        """Возвращает последние строки логов всех потоков."""
        with self._log_lock:
            return {
                rid: list(d)[-limit:]
                for rid, d in self._logs.items()
            }

    # ------------------------------------------------------------------
    # Очистка ресурсов потока (вызывается воркером при завершении)
    # ------------------------------------------------------------------
    def cleanup(self, route_id: str) -> None:
        """Удаляет задачу и статус потока.

        Вызывается воркером в блоке ``finally`` при завершении работы,
        чтобы менеджер не хранил ссылки на завершённые задачи.
        """
        with self._lock:
            self._tasks.pop(route_id, None)
            self._stats.pop(route_id, None)


# Единственный экземпляр менеджера стримера для всего приложения.
stream_manager = StreamManager()
PYEOF_SM
echo "  ✔ app/services/stream_manager.py"

# ------------------------------------------------------------
# Проверка, что файл создан и не пуст
# ------------------------------------------------------------
if [ ! -s "$PROJECT_DIR/app/services/stream_manager.py" ]; then
  echo "❌ ОШИБКА: файл пуст или не создан!" >&2
  exit 1
fi

echo "✅ Менеджер стримера готов (с правильным синтаксисом)."
echo "ℹ️  Воркер захвата (с исправленным _check_host) будет создан скриптом 06."