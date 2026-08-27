#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 33: ИСПРАВЛЕНИЕ ОТОБРАЖЕНИЯ ПОТОКА
#  ------------------------------------------------------------
#  Исправляет две проблемы:
#    1. Поток не отображается после включения камеры без
#       перезагрузки страницы
#    2. Статус мигает «подключение» даже если камера подключена
#
#  Что делает:
#    1. CameraCard.jsx — видео всегда рендерится (не условно),
#       плеер корректно пересоздаётся при изменении статуса
#    2. stream_manager.py — статус не удаляется при остановке
#       воркера, а устанавливается в «недоступна»
#    3. useStreamStatus.js — слияние статусов вместо полной
#       замены, чтобы не терять данные при пересинхронизации
#
#  Запуск:   bash 33_fix_stream_display.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. CameraCard.jsx — видео всегда рендерится, плеер корректно
#    пересоздаётся при изменении статуса
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/CameraCard.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — карточка камеры (видеостена)
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v33):
//  • Видео ВСЕГДА рендерится (не условно) — это гарантирует,
//    что videoRef.current доступен в момент выполнения эффекта
//  • Плеер корректно пересоздаётся при изменении статуса
//    (включение/выключение камеры)
//  • Устранена проблема «поток не появляется без перезагрузки»
// ============================================================
import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'

export default function CameraCard({ camera, status, onContextMenu, onFullscreen }) {
  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  const [error, setError] = useState(null)

  // В сетке субпоток; если его нет — основной.
  const hasSub = camera.sub_url && camera.sub_url.trim() !== '' &&
                 camera.sub_url !== camera.main_url
  const routeId = hasSub ? `${camera.id}_sub` : `${camera.id}_main`
  const streamUrl = `/hls/camera/${routeId}/index.m3u8`

  // ИСПРАВЛЕНО (v33): shouldPlay не зависит от статуса «недоступна»,
  // т.к. статус может задерживаться. Достаточно флага включена.
  const shouldPlay = camera.enabled

  // ИСПРАВЛЕНО (v33): эффект корректно управляет плеером при
  // изменении статуса камеры. Видео элемент всегда рендерится,
  // поэтому videoRef.current гарантированно доступен.
  useEffect(() => {
    const video = videoRef.current

    // Если не нужно воспроизводить — очищаем плеер и выходим.
    if (!shouldPlay) {
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
      if (video) {
        video.removeAttribute('src')
        video.load()
      }
      setError(null)
      return
    }

    // Если видео элемента нет (не должно случаться, т.к. он
    // всегда рендерится), выходим.
    if (!video) return

    setError(null)

    if (Hls.isSupported()) {
      const hls = new Hls({
        liveSyncDurationCount: 2,
        liveMaxLatencyDurationCount: 4,
        lowLatencyMode: true,
      })
      hls.loadSource(streamUrl)
      hls.attachMedia(video)
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {})
      })
      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          setError('Поток недоступен')
          hls.destroy()
          hlsRef.current = null
        }
      })
      hlsRef.current = hls
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = streamUrl
      video.play().catch(() => setError('Не удалось воспроизвести'))
    }

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
    }
  }, [streamUrl, shouldPlay])

  const handleDoubleClick = () => {
    if (onFullscreen) onFullscreen(camera)
  }

  const getStatusDot = () => {
    if (!camera.enabled) return 'status-dot offline'
    if (status === 'в_сети') return 'status-dot online'
    if (status === 'недоступна') return 'status-dot offline'
    return 'status-dot connecting'
  }

  const statusText = !camera.enabled ? 'Отключена'
    : status === 'в_сети' ? 'Онлайн'
    : status === 'недоступна' ? 'Недоступна'
    : 'Подключение'

  return (
    <div
      className="camera-card"
      onContextMenu={(e) => {
        e.preventDefault()
        if (onContextMenu) onContextMenu(camera, e.clientX, e.clientY)
      }}
      onDoubleClick={handleDoubleClick}
      style={{ cursor: 'pointer' }}
      title={`${camera.name} — ${statusText}. Двойной клик — на весь экран`}
    >
      {/* ИСПРАВЛЕНО (v33): видео ВСЕГДА рендерится (не условно).
          Это гарантирует, что videoRef.current доступен в момент
          выполнения эффекта и плеер создаётся корректно. */}
      <video
        ref={videoRef}
        muted
        playsInline
        className="camera-video"
      />

      {/* Шапка: наложение сверху, полупрозрачный градиент */}
      <div className="camera-card-header">
        <span className="camera-name" title={camera.name}>
          {camera.name}
        </span>
        <span className={getStatusDot()} title={statusText} />
      </div>

      {/* Бейдж аудио: наложение снизу справа */}
      {camera.enabled && status === 'в_сети' && (
        <div className="camera-audio-badge">
          {camera.audio ? '🔊' : '🔇'}
        </div>
      )}

      {/* Бейдж типа потока: наложение снизу слева */}
      {camera.enabled && status === 'в_сети' && (
        <div className="camera-stream-badge">
          {hasSub ? 'SUB' : 'MAIN'}
        </div>
      )}

      {/* Ошибка */}
      {error && (
        <div className="camera-overlay-text" style={{ color: '#dc2626' }}>
          {error}
        </div>
      )}

      {/* Камера отключена */}
      {!camera.enabled && (
        <div className="camera-overlay-text">
          Отключена
        </div>
      )}

      {/* Камера включена, но недоступна */}
      {camera.enabled && status === 'недоступна' && (
        <div className="camera-overlay-text">
          Недоступна
        </div>
      )}
    </div>
  )
}
JSXEOF
echo "  ✔ CameraCard.jsx (видео всегда рендерится, плеер пересоздаётся)"

# ============================================================
# 2. useStreamStatus.js — слияние статусов вместо полной замены
# ============================================================
cat > "$PROJECT_DIR/frontend/src/hooks/useStreamStatus.js" << 'JSEOF'
// ============================================================
//  GRYPHONE — хук подписки на события в реальном времени
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v33):
//  • Слияние статусов вместо полной замены — статусы не
//    теряются при пересинхронизации воркеров
//  • Устранено мигание статуса «подключение»
// ============================================================
import { useState, useEffect, useRef } from 'react'

export default function useStreamStatus() {
  const [stats, setStats] = useState({})
  // ИСПРАВЛЕНО (v33): хранилище последних известных статусов.
  // При получении новых данных сливаем с существующими, чтобы
  // не терять статусы при временном отсутствии в ответе.
  const lastStatsRef = useRef({})

  useEffect(() => {
    const source = new EventSource('/api/stream_status')

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        // ИСПРАВЛЕНО (v33): слияние с последним известным статусом.
        // Если маршрут отсутствует в новых данных, сохраняем
        // последний известный статус, чтобы не мигало «подключение».
        const merged = { ...lastStatsRef.current, ...data }
        lastStatsRef.current = merged
        setStats(merged)
      } catch (e) {
        console.error('Ошибка разбора данных:', e)
      }
    }

    source.onerror = () => {
      console.warn('Ошибка подписки на события')
    }

    return () => {
      source.close()
    }
  }, [])

  return stats
}
JSEOF
echo "  ✔ useStreamStatus.js (слияние статусов)"

# ============================================================
# 3. stream_manager.py — статус не удаляется, а устанавливается
#    в «недоступна» при остановке воркера
# ============================================================
cat > "$PROJECT_DIR/app/services/stream_manager.py" << 'PYEOF_SM'
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
PYEOF_SM
echo "  ✔ stream_manager.py (статус не удаляется при остановке)"

# ============================================================
# 4. hls_worker.py — при отключении камеры не завершать воркер
#    мгновенно, а дать завершиться штатно
# ============================================================
cat > "$PROJECT_DIR/app/workers/hls_worker.py" << 'PYEOF_HLS'
# -*- coding: utf-8 -*-
"""
app/workers/hls_worker.py
=========================
Воркер захвата одного потока камеры.

ИСПРАВЛЕНО (v33):
• При отключении камеры воркер завершается штатно и устанавливает
  статус «недоступна» — фронтенд сразу показывает правильный статус
"""
import asyncio
import logging
import re
import subprocess
import time
from pathlib import Path

from app.config import config
from app.services.camera_service import camera_service
from app.utils.ffmpeg import (
    build_ffmpeg_cmd,
    check_host,
    decide_stream_mode,
    probe_camera,
)

logger = logging.getLogger(__name__)

_STATS_RE = re.compile(
    r"frame=\s*(\d+)\s*fps=\s*([\d.]+)\s*q=\s*([\d.-]+)\s*"
    r"size=\s*([\d.]+[a-zA-Z]+)\s*time=(\S+)\s*bitrate=([\d.]+[a-zA-Z/]+)"
)


async def hls_worker(url: str, route_id: str, cam_id: str, manager) -> None:
    """Воркер захвата одного потока."""
    cfg = config.all()
    hls_cache = cfg.get("paths", {}).get("hls_cache", "hls_cache")
    ff_cfg = cfg.get("ffmpeg", {})
    global_cfg = ff_cfg.get("global", {})
    app_cfg = cfg.get("app", {})

    backoff = 1
    backoff_max = app_cfg.get("backoff_max", 30)

    # Создаём директорию для сегментов.
    project_root = Path(__file__).parent.parent.parent
    out_dir = project_root / hls_cache / "camera" / route_id
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error("❌ Не удалось создать директорию %s: %s", out_dir, e)
        return

    logger.info("🔍 Воркер запущен: %s", route_id)
    try:
        while True:
            cam = camera_service.get_camera(cam_id)
            if not cam or not cam.enabled:
                logger.info("⏹ Камера отключена, воркер завершается: %s", route_id)
                # ИСПРАВЛЕНО (v33): устанавливаем статус «недоступна»
                # при штатном завершении, чтобы фронтенд сразу
                # показал правильный статус без мигания.
                manager.set_status(route_id, "недоступна", "Камера отключена")
                break

            manager.set_status(route_id, "подключение", "Подключение...")

            probe_timeout = global_cfg.get("probe_timeout", 3)
            if not await check_host(url, timeout=probe_timeout):
                manager.set_status(route_id, "недоступна", "Хост недоступен")
                logger.warning("⚠️ Хост недоступен: %s", route_id)
                await asyncio.sleep(min(backoff * 2, 15))
                backoff = min(backoff * 2, 15)
                continue

            backoff = 1
            manager.clear_log(route_id)

            try:
                loop = asyncio.get_running_loop()
                codec, profile, pix_fmt = await loop.run_in_executor(
                    None, probe_camera, url, global_cfg
                )
            except Exception:
                codec, profile, pix_fmt = "unknown", "unknown", "unknown"

            mode_cfg = ff_cfg.get("mode", "auto")
            if mode_cfg == "copy":
                mode = "copy"
            elif mode_cfg == "transcode":
                mode = "transcode"
            else:
                mode = decide_stream_mode(codec, profile, pix_fmt)
            logger.info("✅ %s: режим=%s (кодек=%s)", route_id, mode, codec)

            while True:
                cam = camera_service.get_camera(cam_id)
                if not cam or not cam.enabled:
                    # ИСПРАВЛЕНО (v33): устанавливаем статус при
                    # отключении камеры внутри цикла.
                    manager.set_status(route_id, "недоступна", "Камера отключена")
                    break
                manager.set_status(route_id, "подключение", "Запуск потока...")

                cmd = build_ffmpeg_cmd(url, route_id, mode, ff_cfg, str(project_root / hls_cache))

                # Если у камеры audio=false, добавляем флаг -an.
                if not cam.audio:
                    filtered = []
                    skip_next = False
                    for i, arg in enumerate(cmd):
                        if skip_next:
                            skip_next = False
                            continue
                        if arg in ("-c:a", "-b:a", "-ar", "-ac"):
                            skip_next = True
                            continue
                        filtered.append(arg)
                    try:
                        f_index = filtered.index("-f")
                        filtered.insert(f_index, "-an")
                    except ValueError:
                        filtered.append("-an")
                    cmd = filtered
                    logger.info("🔇 %s: аудио отключено", route_id)

                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                    )

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
                                    m = _STATS_RE.search(text)
                                    if m:
                                        manager.set_status(
                                            route_id, "в_сети", "Поток активен",
                                            metrics={
                                                "fps": m.group(2),
                                                "bitrate": m.group(6),
                                                "time": m.group(5),
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
                break
    except asyncio.CancelledError:
        logger.info("⏹ Воркер отменён: %s", route_id)
        # ИСПРАВЛЕНО (v33): при отмене (например, при выключении камеры
        # через контекстное меню) устанавливаем статус «недоступна».
        manager.set_status(route_id, "недоступна", "Камера отключена")
    finally:
        # ИСПРАВЛЕНО (v33): cleanup не удаляет статус, а сохраняет
        # его как «недоступна» (см. обновлённый stream_manager.py).
        manager.cleanup(route_id)
        logger.info("🧹 Воркер завершён: %s", route_id)
PYEOF_HLS
echo "  ✔ hls_worker.py (статус при отключении камеры)"

# ------------------------------------------------------------
# Проверка
# ------------------------------------------------------------
for f in frontend/src/components/CameraCard.jsx frontend/src/hooks/useStreamStatus.js app/services/stream_manager.py app/workers/hls_worker.py; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Исправления применены"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что исправлено:"
echo ""
echo "Проблема 1: Поток не отображается без перезагрузки"
echo "  Причина: видео рендерилось условно, и videoRef.current"
echo "  был null в момент выполнения эффекта"
echo "  Решение: видео ВСЕГДА рендерится, плеер создаётся"
echo "  когда shouldPlay становится true"
echo ""
echo "Проблема 2: Статус мигает «подключение»"
echo "  Причина: при остановке воркера статус удалялся из словаря,"
echo "  и фронтенд получал undefined → «подключение»"
echo "  Решение:"
echo "    • stream_manager: статус устанавливается в «недоступна»"
echo "      вместо удаления"
echo "    • useStreamStatus: слияние статусов вместо полной замены"
echo "    • hls_worker: при отключении камеры устанавливается"
echo "      «недоступна» перед завершением воркера"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 (Ctrl+Shift+R)"
echo "  4. Включите/выключите камеру через контекстное меню —"
echo "     поток появится/исчезнет БЕЗ перезагрузки страницы"