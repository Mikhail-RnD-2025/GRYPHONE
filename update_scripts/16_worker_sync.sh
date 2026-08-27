#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 16: ЗАПУСК И СИНХРОНИЗАЦИЯ ВОРКЕРОВ
#  ------------------------------------------------------------
#  Исправляет баг: воркеры не стартовали, потому что никто не
#  вызывал stream_manager.sync() при старте и при изменении камер.
#
#  Что делает:
#    1. Обновляет app/__init__.py:
#       - добавляет импорт camera_service;
#       - вызывает stream_manager.sync() после старта цикла.
#    2. Обновляет app/services/camera_service.py:
#       - добавляет вызов stream_manager.sync() в save_cameras,
#         toggle_camera, switch_set.
#
#  Запуск:   bash 16_worker_sync.sh
#  После:    python main.py → в логах появятся "🚀 Запущен воркер: ..."
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. app/__init__.py — фабрика с раздачей фронтенда + запуск воркеров
# ============================================================
cat > "$PROJECT_DIR/app/__init__.py" << 'PYEOF_FACTORY'
# -*- coding: utf-8 -*-
"""
app/__init__.py
===============
Фабрика приложения: создаёт Flask, регистрирует API-роуты, раздаёт
собранный фронтенд из frontend/dist/ (один порт), запускает
менеджер стримера и воркеры захвата.
"""
import logging
import threading
from pathlib import Path
from flask import Flask, send_from_directory, abort

from app.config import config
from app.services.stream_manager import stream_manager
from app.services.camera_service import camera_service
from app.workers.cleanup_worker import cleanup_worker
from app.routes import register_routes

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Создаёт и настраивает приложение."""
    # Корневая директория проекта (родитель app/).
    project_root = Path(__file__).parent.parent
    frontend_dist = project_root / "frontend" / "dist"

    # Отключаем встроенную раздачу статики Flask.
    app = Flask(__name__, static_folder=None)

    # Настраиваем логирование.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Регистрируем раздачу фронтенда.
    _register_frontend(app, frontend_dist)

    # Регистрируем API-роуты.
    register_routes(app)

    # Запускаем менеджер стримера (асинхронный цикл в отдельном потоке).
    stream_manager.start()

    # ЗАПУСКАЕМ ВОРКЕРЫ для всех ВКЛЮЧЁННЫХ камер.
    # Без этого вызова цикл крутился вхолостую, а воркеры не стартовали.
    stream_manager.sync(camera_service.enabled_cameras())

    # Запускаем фоновую очистку кэша.
    cleanup_thread = threading.Thread(
        target=cleanup_worker, daemon=True, name="CleanupWorker"
    )
    cleanup_thread.start()

    logger.info("✅ Приложение создано и настроено")
    return app


def _register_frontend(app: Flask, dist_dir: Path) -> None:
    """Регистрирует раздачу собранного фронтенда + SPA-фоллбэк."""

    @app.route("/")
    def index():
        """Главная страница: отдаёт собранный index.html."""
        if not (dist_dir / "index.html").is_file():
            return (
                "<h3>Фронтенд не собран</h3>"
                "<p>Выполните: <code>bash build_frontend.sh</code></p>",
                503,
            )
        return send_from_directory(str(dist_dir), "index.html")

    @app.route("/assets/<path:filename>")
    def assets(filename):
        """Отдаёт ассеты фронтенда (JS, CSS, картинки)."""
        assets_dir = dist_dir / "assets"
        if not assets_dir.is_dir():
            abort(404)
        return send_from_directory(str(assets_dir), filename)

    @app.route("/<path:filename>")
    def static_files(filename):
        """Отдаёт статические файлы и SPA-фоллбэк."""
        file_path = dist_dir / filename
        if file_path.is_file():
            return send_from_directory(str(dist_dir), filename)
        # SPA-фоллбэк для React Router.
        index_path = dist_dir / "index.html"
        if not index_path.is_file():
            abort(404)
        return send_from_directory(str(dist_dir), "index.html")
PYEOF_FACTORY
echo "  ✔ app/__init__.py (добавлен запуск воркеров)"

# ============================================================
# 2. app/services/camera_service.py — с вызовами синхронизации
# ============================================================
cat > "$PROJECT_DIR/app/services/camera_service.py" << 'PYEOF_CAM'
# -*- coding: utf-8 -*-
"""
app/services/camera_service.py
==============================
Сервис управления камерами и наборами камер.

Отвечает за:
  - загрузку и сохранение камер и наборов в БД;
  - доступ к списку камер (всех, включённых, по наборам);
  - включение/выключение камер и обновление комментариев;
  - переключение активного набора;
  - синхронизацию воркеров при изменении камер.

Использует репозиторий из ``app.database`` и модели из ``app.models``.
"""
import logging
from typing import Dict, List, Optional

from app.database import db
from app.models import Camera, Set

logger = logging.getLogger(__name__)


class CameraService:
    """Управление камерами и наборами камер."""

    CAMERAS_KEY = "cameras"
    SETS_KEY = "sets"

    def __init__(self):
        self._cameras: Dict[str, Camera] = {}
        self._sets: Dict[str, Set] = {}
        self._default_set: str = ""
        self._current_set: str = ""
        self._load()

    # ------------------------------------------------------------------
    # Загрузка из БД
    # ------------------------------------------------------------------
    def _load(self) -> None:
        """Загружает камеры и наборы из БД в память."""
        raw_cameras = db.get(self.CAMERAS_KEY, []) or []
        self._cameras = {}
        for raw in raw_cameras:
            cam = Camera.from_raw(raw)
            if cam:
                self._cameras[cam.id] = cam

        raw_sets = db.get(self.SETS_KEY, {"default_set": "", "sets": {}}) or {}
        sets_dict = raw_sets.get("sets", {}) if isinstance(raw_sets, dict) else {}
        self._sets = {
            set_id: Set.from_raw(set_id, raw)
            for set_id, raw in sets_dict.items()
        }

        self._default_set = (
            raw_sets.get("default_set", "") if isinstance(raw_sets, dict) else ""
        )
        if not self._default_set or self._default_set not in self._sets:
            self._default_set = next(iter(self._sets), "")
        self._current_set = self._default_set

    def reload(self) -> None:
        """Перечитывает камеры и наборы из БД."""
        self._load()

    # ------------------------------------------------------------------
    # Доступ к камерам
    # ------------------------------------------------------------------
    def all_cameras(self) -> List[Camera]:
        """Возвращает список всех камер."""
        return list(self._cameras.values())

    def enabled_cameras(self) -> List[Camera]:
        """Возвращает список включённых камер."""
        return [c for c in self._cameras.values() if c.enabled]

    def get_camera(self, cam_id: str) -> Optional[Camera]:
        """Возвращает камеру по идентификатору или ``None``."""
        return self._cameras.get(cam_id)

    # ------------------------------------------------------------------
    # Изменение камер (с синхронизацией воркеров)
    # ------------------------------------------------------------------
    def save_cameras(self, raw_list: List[dict]) -> int:
        """Сохраняет список камер из "сырых" словарей."""
        self._cameras = {}
        clean = []
        for raw in raw_list:
            cam = Camera.from_raw(raw)
            if cam:
                self._cameras[cam.id] = cam
                clean.append(cam.to_dict())
        db.save(self.CAMERAS_KEY, clean)
        # Синхронизируем воркеры с новым списком камер.
        self._sync_workers()
        return len(clean)

    def toggle_camera(self, cam_id: str, enabled: bool) -> Optional[Camera]:
        """Включает/выключает камеру."""
        cam = self._cameras.get(cam_id)
        if not cam:
            return None
        cam.enabled = bool(enabled)
        self._persist_cameras()
        # Синхронизируем воркеры.
        self._sync_workers()
        return cam

    def update_comment(self, cam_id: str, comment: str) -> Optional[Camera]:
        """Обновляет комментарий камеры."""
        cam = self._cameras.get(cam_id)
        if not cam:
            return None
        cam.comment = str(comment)
        self._persist_cameras()
        return cam

    def _persist_cameras(self) -> None:
        """Сохраняет текущий список камер в БД."""
        db.save(self.CAMERAS_KEY, [c.to_dict() for c in self._cameras.values()])

    # ------------------------------------------------------------------
    # Доступ к наборам
    # ------------------------------------------------------------------
    def all_sets(self) -> Dict[str, Set]:
        """Возвращает словарь всех наборов."""
        return dict(self._sets)

    def get_set(self, set_id: str) -> Optional[Set]:
        """Возвращает набор по идентификатору или ``None``."""
        return self._sets.get(set_id)

    def default_set_id(self) -> str:
        """Возвращает идентификатор набора по умолчанию."""
        return self._default_set

    def current_set_id(self) -> str:
        """Возвращает идентификатор активного набора."""
        return self._current_set

    def current_set_cameras(self) -> List[Camera]:
        """Возвращает камеры активного набора (в порядке набора)."""
        current = self._sets.get(self._current_set)
        if not current:
            return []
        result = []
        for cam_id in current.camera_ids:
            cam = self._cameras.get(cam_id)
            if cam:
                result.append(cam)
        return result

    # ------------------------------------------------------------------
    # Изменение наборов (с синхронизацией воркеров)
    # ------------------------------------------------------------------
    def save_sets(self, raw: dict) -> bool:
        """Сохраняет наборы из "сырого" словаря."""
        if not isinstance(raw, dict) or "sets" not in raw:
            return False
        sets_dict = raw.get("sets", {})
        for _set_id, set_data in sets_dict.items():
            if isinstance(set_data, dict):
                set_data.setdefault("aspect_ratio", "16:9")
                set_data.setdefault("max_rows", 0)
                set_data.setdefault("max_columns", 2)
        self._sets = {
            set_id: Set.from_raw(set_id, set_data)
            for set_id, set_data in sets_dict.items()
        }
        self._default_set = raw.get("default_set", "") or self._default_set
        if self._current_set not in self._sets:
            self._current_set = self._default_set
        db.save(self.SETS_KEY, raw)
        return True

    def switch_set(self, set_id: str) -> bool:
        """Переключает активный набор."""
        if not set_id or set_id not in self._sets:
            return False
        self._current_set = set_id
        # Синхронизируем воркеры (набор мог изменить список камер).
        self._sync_workers()
        return True

    # ------------------------------------------------------------------
    # Синхронизация воркеров
    # ------------------------------------------------------------------
    def _sync_workers(self) -> None:
        """Вызывает синхронизацию воркеров с текущим списком камер.

        Используется отложенный импорт, чтобы избежать циклической
        зависимости: ``camera_service`` → ``stream_manager`` → ``hls_worker``
        → ``camera_service``.
        """
        from app.services.stream_manager import stream_manager
        stream_manager.sync(self.all_cameras())


# Единственный экземпляр сервиса камер.
camera_service = CameraService()
PYEOF_CAM
echo "  ✔ app/services/camera_service.py (добавлена синхронизация воркеров)"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in app/__init__.py app/services/camera_service.py; do
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
echo "📋 Что изменилось:"
echo "  • app/__init__.py: после старта цикла вызывается"
echo "    stream_manager.sync(camera_service.enabled_cameras())"
echo "  • app/services/camera_service.py: методы save_cameras,"
echo "    toggle_camera, switch_set вызывают stream_manager.sync()"
echo ""
echo "🚀 Запустите:  python main.py"
echo "   В логах появятся строки:"
echo "   🚀 Запущен воркер: <ид_камеры>_main"
echo "   🚀 Запущен воркер: <ид_камеры>_sub"