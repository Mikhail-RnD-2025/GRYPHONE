#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py
Точка входа приложения GPYPHONE v15.0.0 (ASGI/Quart)
Отвечает за: инициализацию, загрузку конфига, запуск фоновых задач и HTTP-сервера.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from quart import Quart

# ==========================================================================
# ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ ДЛЯ WINDOWS (Python 3.10+)
# Предотвращает ошибки "Event loop is closed" и "closed pipe" при завершении
# ==========================================================================
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Локальные модули
import state
from config import default_cfg, merge_dicts
from database import DBManager
import routes
import workers
import archive
import stream_engine

# ==========================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ==========================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# ==========================================================================
# ФУНКЦИЯ СТАРТА (ЗАПУСКАЕТСЯ ОДИН РАЗ ПРИ ИНИЦИАЛИЗАЦИИ СЕРВЕРА)
# ==========================================================================
async def on_startup():
    """Инициализация БД, загрузка конфигов, очистка кэша, запуск фоновых задач."""
    logger.info("🚀 Инициализация GPYPHONE...")

    try:
        # 1. Инициализация базы данных
        db = DBManager()
        await db.init()

        # 2. Загрузка конфигурации
        cfg = default_cfg()
        loaded_cfg = await db.load("config")
        if loaded_cfg:
            merge_dicts(cfg, loaded_cfg)
        state.CFG.update(cfg)

        # 3. Загрузка камер
        cams_data = await db.load("cameras")
        if cams_data:
            for cam in cams_data:
                if cam.get("id"):
                    state.CAMERAS_DB[cam["id"]] = cam

        # 4. Загрузка наборов камер
        sets_data = await db.load("sets")
        if sets_data:
            state.CAMERA_SETS.update(sets_data.get("sets", {}))
            state.CFG["app"]["default_set"] = sets_data.get("default_set", "")

        logger.info(f"✅ Загружено камер: {len(state.CAMERAS_DB)}, наборов: {len(state.CAMERA_SETS)}")

        # 5. Очистка зависших процессов FFmpeg (если функция существует)
        if hasattr(stream_engine, 'cleanup_orphaned_ffmpeg'):
            await stream_engine.cleanup_orphaned_ffmpeg()

        # 6. Очистка старого HLS-кэша
        hls_dir = Path(state.CFG.get("paths", {}).get("hls_cache", "hls_cache"))
        if hls_dir.exists():
            for f in hls_dir.rglob("*"):
                if f.is_file() and f.suffix in ('.m3u8', '.mp4', '.m4s', '.tmp', '.ts'):
                    try:
                        f.unlink()
                    except Exception:
                        pass
            logger.info("🧹 HLS-кэш очищен.")

        # 7. Запуск фоновых асинхронных задач
        asyncio.create_task(workers.sync_camera_streams())
        asyncio.create_task(archive.archive_worker_async())

        # ✅ ОБНОВЛЕННАЯ ВЕРСИЯ
        logger.info("🚀 GPYPHONE v15.0.0 (ASGI) успешно запущен!")

    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при запуске: {e}", exc_info=True)
        sys.exit(1)


# ==========================================================================
# ФАБРИКА ПРИЛОЖЕНИЯ QUART
# ==========================================================================
def create_app() -> Quart:
    """Создает и настраивает экземпляр ASGI-приложения."""
    app = Quart(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "rtsp_viewer_secure_key_2026")

    # Регистрация HTTP/SSE маршрутов
    routes.register_routes(app)

    # Отдача статических файлов React из dist/
    from quart import send_from_directory
    
    @app.route('/assets/<path:filename>')
    async def serve_assets(filename):
        return await send_from_directory('frontend/dist/assets', filename)
    
    @app.route('/favicon.svg')
    async def serve_favicon():
        return await send_from_directory('frontend/dist', 'favicon.svg')
    
    @app.route('/icons.svg')
    async def serve_icons():
        return await send_from_directory('frontend/dist', 'icons.svg')
    
    # Основной маршрут для React SPA
    @app.route('/react')
    @app.route('/react/')
    async def serve_react_app():
        return await send_from_directory('frontend/dist', 'index.html')

    # Привязка функции запуска к событию before_serving
    @app.before_serving
    async def startup_hook():
        await on_startup()

    # ==========================================================================
    # ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Корректное завершение работы (Graceful Shutdown)
    # ==========================================================================
    @app.after_serving
    async def shutdown_hook():
        logger.info("🛑 Завершение работы сервера. Остановка всех процессов FFmpeg...")

        # Безопасное получение списка активных процессов
        procs_to_kill = []
        if hasattr(state, 'ACTIVE_PROCS'):
            procs_to_kill = list(state.ACTIVE_PROCS.values())
        elif hasattr(stream_engine, 'worker') and hasattr(stream_engine.worker, 'ACTIVE_PROCS'):
            procs_to_kill = list(stream_engine.worker.ACTIVE_PROCS.values())

        for info in procs_to_kill:
            proc = info.get("proc") if isinstance(info, dict) else info
            route_id = info.get("route_id", "unknown") if isinstance(info, dict) else "unknown"

            # Если процесс всё ещё работает (returncode is None)
            if proc and proc.returncode is None:
                try:
                    logger.info(f"⏹️ Остановка FFmpeg для {route_id} (PID: {proc.pid})...")
                    proc.terminate()
                    # Ждем до 2 секунд, пока процесс закроется корректно
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ Процесс {route_id} не ответил, принудительное завершение (kill)...")
                    proc.kill()
                    await proc.wait()
                except Exception as e:
                    logger.error(f"❌ Ошибка при остановке FFmpeg ({route_id}): {e}")

        logger.info("✅ Все процессы FFmpeg корректно остановлены. Сервер закрыт.")

    return app


# ==========================================================================
# ЗАПУСК СЕРВЕРА
# ==========================================================================
if __name__ == "__main__":
    try:
        import hypercorn.asyncio
        import hypercorn.config

        config = hypercorn.config.Config()
        config.bind = ["0.0.0.0:5000"]
        config.accesslog = "-"
        config.errorlog = "-"
        config.loglevel = "info"
        # На Windows uvloop не поддерживается, используем стандартный asyncio
        config.worker_class = "asyncio" if os.name == "nt" else "uvloop"

        app = create_app()
        logger.info(f"🌐 Сервер запускается на http://0.0.0.0:5000")
        logger.info("💡 Для остановки нажмите CTRL + C")

        asyncio.run(hypercorn.asyncio.serve(app, config))

    except ImportError:
        # Fallback на встроенный сервер Quart (если hypercorn не установлен)
        logger.warning("⚠️ Hypercorn не найден. Запускаю встроенный сервер Quart.")
        logger.warning("💡 Установите: pip install hypercorn")
        app = create_app()
        app.run(host="0.0.0.0", port=5000)