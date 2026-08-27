# -*- coding: utf-8 -*-
"""
app/services/stream_manager.py
==============================
Сервис управления асинхронными воркерами захвата потоков.

ИСПРАВЛЕНО (v33):
• При остановке воркера статус не удаляется, а устанавливается
  в «недоступна» — устранено мигание «подключение»
• При очистке воркера статус сохраняется как «недоступна»
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
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._tasks: Dict[str, asyncio.Task] = {}
        self._stats: Dict[str, dict] = {}
        self._logs: Dict[str, deque] = {}
        self._lock = threading.RLock()
        self._log_lock = threading.Lock()
        self._started = False
        self._ready_event = threading.Event()

    def start(self) -> None:
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
        asyncio.set_event_loop(self._loop)
        self._loop.call_soon(self._ready_event.set)
        self._loop.run_forever()

    def wait_ready(self, timeout: float = 5.0) -> bool:
        return self._ready_event.wait(timeout)

    def stop(self) -> None:
        if not self._started or self._loop is None:
            return
        for task in list(self._tasks.values()):
            self._loop.call_soon_threadsafe(task.cancel)
        self._tasks.clear()
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._started = False
        logger.info("⏹ Асинхронный цикл стримера остановлен")

    def sync(self, cameras: List[Camera]) -> None:
        if not self._started or self._loop is None:
            logger.warning("⚠️ Стример не запущен, синхронизация отложена")
            return
        asyncio.run_coroutine_threadsafe(self._sync(cameras), self._loop)

    async def _sync(self, cameras: List[Camera]) -> None:
        """Синхронизация воркеров со списком камер."""
        from app.workers.hls_worker import hls_worker

        needed: Dict[str, tuple] = {}
        for cam in cameras:
            if not cam.enabled:
                continue
            needed[cam.main_route_id] = (cam.main_url, cam.id)
            if cam.has_sub_stream:
                needed[cam.sub_route_id] = (cam.sub_url, cam.id)

        with self._lock:
            # Останавливаем воркеры, которых нет в нужном списке.
            for rid in list(self._tasks.keys()):
                if rid not in needed:
                    task = self._tasks.pop(rid)
                    task.cancel()
                    # ИСПРАВЛЕНО (v33): статус НЕ удаляется, а
                    # устанавливается в «недоступна». Это устраняет
                    # мигание «подключение» на фронтенде.
                    self._stats[rid] = {
                        "state": "недоступна",
                        "msg": "Камера отключена",
                        "metrics": {},
                    }
                    logger.info("⏹ Остановлен воркер: %s", rid)
            # Запускаем недостающие воркеры.
            for rid, (url, cam_id) in needed.items():
                if rid not in self._tasks:
                    task = self._loop.create_task(
                        hls_worker(url, rid, cam_id, self)
                    )
                    self._tasks[rid] = task
                    # ИСПРАВЛЕНО (v33): сразу устанавливаем статус
                    # «подключение», чтобы фронтенд не мигал.
                    self._stats[rid] = {
                        "state": "подключение",
                        "msg": "Подключение...",
                        "metrics": {},
                    }
                    logger.info("🚀 Запущен воркер: %s", rid)

    def set_status(self, route_id: str, state: str, msg: str = "",
                   metrics: Optional[dict] = None) -> None:
        with self._lock:
            self._stats[route_id] = {
                "state": state,
                "msg": msg,
                "metrics": metrics or {},
            }

    def get_all_stats(self) -> Dict[str, dict]:
        with self._lock:
            return dict(self._stats)

    def get_status(self, route_id: str) -> Optional[dict]:
        with self._lock:
            return self._stats.get(route_id)

    def add_log(self, route_id: str, line: str, maxlen: int = 500) -> None:
        with self._log_lock:
            if route_id not in self._logs:
                self._logs[route_id] = deque(maxlen=maxlen)
            self._logs[route_id].append(line)

    def clear_log(self, route_id: str) -> None:
        with self._log_lock:
            if route_id in self._logs:
                self._logs[route_id].clear()

    def get_logs(self, limit: int = 100) -> Dict[str, List[str]]:
        with self._log_lock:
            return {
                rid: list(d)[-limit:]
                for rid, d in self._logs.items()
            }

    def cleanup(self, route_id: str) -> None:
        """Удаляет задачу, но сохраняет статус как «недоступна».

        ИСПРАВЛЕНО (v33): статус не удаляется — фронтенд не мигает.
        """
        with self._lock:
            self._tasks.pop(route_id, None)
            self._stats[route_id] = {
                "state": "недоступна",
                "msg": "Камера отключена",
                "metrics": {},
            }


stream_manager = StreamManager()
