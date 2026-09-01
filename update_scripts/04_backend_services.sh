#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 04: СЕРВИСЫ КАМЕР
#  ------------------------------------------------------------
#  Заполняет сервисы бизнес-логики:
#    - app/services/__init__.py       — маркер пакета
#    - app/services/camera_service.py — набор камер (полная реализация)
#    - app/services/config_sync.py    — [каркас с TODO] синхронизация
#                                       с внешними системами
#
#  Запуск:   bash 04_backend_services.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# app/services/__init__.py — маркер пакета
# ============================================================
cat > "$PROJECT_DIR/app/services/__init__.py" << 'PYEOF_INIT'
# -*- coding: utf-8 -*-
"""
Пакет сервисов (бизнес-логика) приложения.

Сервисы:
  - camera_service : управление камерами и наборами
  - stream_manager : управление воркерами захвата и статусами потоков
  - config_sync    : [каркас] синхронизация с внешними системами
"""
PYEOF_INIT
echo "  ✔ app/services/__init__.py"

# ============================================================
# app/services/config_sync.py — [КАРКАС с TODO]
# ============================================================
cat > "$PROJECT_DIR/app/services/config_sync.py" << 'PYEOF_SYNC'
# -*- coding: utf-8 -*-
"""
app/services/config_sync.py
===========================
[КАРКАС] Синхронизация конфигурации и событий с внешними системами.

Этот модуль — задел под будущую интеграцию проекта с внешней платформой
безопасности. Владелец конфигурации камер — сам проект, синхронизация
однонаправленная: отсюда наружу.

Сейчас модуль не выполняет реальных действий. Реализация будет добавлена
на этапе интеграции.
"""

# TODO: Реализовать клиент шины событий для публикации событий наружу.
#       Тип шины и адрес брать из конфигурации (секция "интеграция").

# TODO: Реализовать публикацию событий (камера недоступна, движение и т.д.)
#       в шину событий внешней системы.

# TODO: Реализовать синхронизацию конфигурации камер наружу
#       (однонаправленная: владелец — этот проект).

# TODO: Реализовать обработку режима аутентификации
#       (своя или делегированная внешней системе).


class ConfigSync:
    """Заглушка сервиса синхронизации с внешними системами."""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def publish_event(self, event) -> None:
        """Публикует событие во внешнюю систему.

        .. todo:: Реализовать отправку события в шину событий.
        """
        # TODO: Реализовать отправку события.
        if not self.enabled:
            return

    def sync_cameras(self, cameras) -> None:
        """Синхронизирует конфигурацию камер с внешней системой.

        .. todo:: Реализовать однонаправленную синхронизацию наружу.
        """
        # TODO: Реализовать синхронизацию.
        if not self.enabled:
            return


# Единственный экземпляр (по умолчанию отключён).
config_sync = ConfigSync(enabled=False)
PYEOF_SYNC
echo "  ✔ app/services/config_sync.py"

# ============================================================
# app/services/camera_service.py — набор камер (полная реализация)
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
  - переключение активного набора.

Использует репозиторий из ``app.database`` и модели из ``app.models``.
"""
import logging
from typing import Dict, List, Optional

from app.database import db
from app.models import Camera, Set

logger = logging.getLogger(__name__)


class CameraService:
    """Управление камерами и наборами камер."""

    CAMERAS_KEY = "cameras"   # ключ в БД для списка камер
    SETS_KEY = "sets"         # ключ в БД для структуры наборов

    def __init__(self):
        self._cameras: Dict[str, Camera] = {}      # {id: камера}
        self._sets: Dict[str, Set] = {}            # {id набора: набор}
        self._default_set: str = ""                # набор по умолчанию
        self._current_set: str = ""                # активный набор
        self._load()

    # ------------------------------------------------------------------
    # Загрузка из БД
    # ------------------------------------------------------------------
    def _load(self) -> None:
        """Загружает камеры и наборы из БД в память."""
        # Камеры.
        raw_cameras = db.get(self.CAMERAS_KEY, []) or []
        self._cameras = {}
        for raw in raw_cameras:
            cam = Camera.from_raw(raw)
            if cam:
                self._cameras[cam.id] = cam

        # Наборы.
        raw_sets = db.get(self.SETS_KEY, {"default_set": "", "sets": {}}) or {}
        sets_dict = raw_sets.get("sets", {}) if isinstance(raw_sets, dict) else {}
        self._sets = {
            set_id: Set.from_raw(set_id, raw)
            for set_id, raw in sets_dict.items()
        }

        # Определяем набор по умолчанию.
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
    # Изменение камер
    # ------------------------------------------------------------------
    def save_cameras(self, raw_list: List[dict]) -> int:
        """Сохраняет список камер из "сырых" словарей.

        Возвращает число сохранённых (корректных) камер.
        """
        self._cameras = {}
        clean = []
        for raw in raw_list:
            cam = Camera.from_raw(raw)
            if cam:
                self._cameras[cam.id] = cam
                clean.append(cam.to_dict())
        db.save(self.CAMERAS_KEY, clean)
        return len(clean)

    def toggle_camera(self, cam_id: str, enabled: bool) -> Optional[Camera]:
        """Включает/выключает камеру. Возвращает камеру или ``None``."""
        cam = self._cameras.get(cam_id)
        if not cam:
            return None
        cam.enabled = bool(enabled)
        self._persist_cameras()
        return cam

    def update_comment(self, cam_id: str, comment: str) -> Optional[Camera]:
        """Обновляет комментарий камеры. Возвращает камеру или ``None``."""
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
    # Изменение наборов
    # ------------------------------------------------------------------
    def save_sets(self, raw: dict) -> bool:
        """Сохраняет наборы из "сырого" словаря.

        Ожидается структура: ``{"набор_по_умолчанию": ..., "наборы": {...}}``.
        Возвращает ``True`` при успехе.
        """
        if not isinstance(raw, dict) or "sets" not in raw:
            return False
        sets_dict = raw.get("sets", {})
        # Дозаполняем умолчания для каждого набора.
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
        """Переключает активный набор. Возвращает ``True`` при успехе."""
        if not set_id or set_id not in self._sets:
            return False
        self._current_set = set_id
        return True


# Единственный экземпляр сервиса камер.
camera_service = CameraService()
PYEOF_CAM
echo "  ✔ app/services/camera_service.py"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in app/services/__init__.py app/services/config_sync.py app/services/camera_service.py; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo "✅ Сервисы камер готовы (с правильным синтаксисом)."
echo "ℹ️  Управление воркерами (стример) будет создано скриптом 05."