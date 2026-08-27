#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 39: ФУНДАМЕНТ КЛАСТЕРА + ОБЩИЙ ХЕЛПЕР
#  ------------------------------------------------------------
#  Создаёт два артефакта:
#    1. update_scripts/_lib.sh — общая библиотека для всех
#       скриптов (надёжное определение Python, логирование).
#       Решает проблему с открытием Windows Store при вызове
#       несуществующей команды `python3`.
#
#    2. Каркас кластера (ЗАГОТОВКИ, режим «не разрушать»):
#       • app/cluster/models.py    — Node, NodeRole, CameraAssignment
#       • app/cluster/registry.py  — реестр узлов
#       • app/cluster/scheduler.py — распределение камер по узлам
#       • app/cluster/roles/       — роли серверов по задачам
#       • app/core/node.py         — идентификация текущего узла
#
#  ЗАПУСК:   bash update_scripts/39_cluster_foundation.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# ЧАСТЬ 1: Создаём общую библиотеку _lib.sh
# ============================================================
mkdir -p "$SCRIPT_DIR"

cat > "$SCRIPT_DIR/_lib.sh" << 'LIBEOF'
# ============================================================
#  GRYPHONE — общая библиотека для скриптов обновления
#  ------------------------------------------------------------
#  Подключается в начале каждого скрипта:
#    source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_lib.sh"
#
#  Предоставляет:
#    • Надёжное определение Python (без Windows Store)
#    • Функции логирования
#    • Определение корня проекта
#    • Безопасные проверки файлов (режим "не разрушать")
# ============================================================

# Корень проекта (скрипты лежат в update_scripts/)
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$LIB_DIR")}"

# ---------- Логирование ----------
log_info()  { echo "ℹ️  $*"; }
log_ok()    { echo "  ✔ $*"; }
log_warn()  { echo "⚠️  $*"; }
log_error() { echo "❌ $*" >&2; }

# ---------- Надёжное определение Python ----------
# На Windows команды `python3` часто нет, и система открывает
# Microsoft Store ("python install manager"). Поэтому проверяем
# несколько вариантов и берём первый реально работающий.
_detect_python() {
    local cmd
    for cmd in python python3 py; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" --version >/dev/null 2>&1; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    # Отдельно пробуем `py -3` (Windows Python Launcher)
    if command -v py >/dev/null 2>&1; then
        if py -3 --version >/dev/null 2>&1; then
            echo "py -3"
            return 0
        fi
    fi
    return 1
}

PYTHON="$(_detect_python || true)"

# Завершить работу, если Python не найден, с подсказкой.
require_python() {
    if [ -z "$PYTHON" ]; then
        log_error "Не найден работающий интерпретатор Python."
        echo "   Установите Python: https://www.python.org/downloads/"
        echo "   и поставьте галочку 'Add Python to PATH' при установке."
        echo ""
        echo "   Если вместо запуска открывается Microsoft Store:"
        echo "   Параметры → Приложения → Дополнительные возможности →"
        echo "   Псевдонимы выполнения приложений → отключите"
        echo "   'Установщик приложений' (python.exe / python3.exe)"
        exit 1
    fi
    log_info "Интерпретатор Python: $PYTHON ($($PYTHON --version 2>&1))"
}

# ---------- Безопасные проверки файлов ----------
# Проверить, что файл создан и не пуст (иначе выйти с ошибкой).
require_file() {
    local f="$1"
    if [ ! -s "$PROJECT_DIR/$f" ]; then
        log_error "Файл $f пуст или не создан!"
        exit 1
    fi
    log_ok "$f"
}

# Вернуть 0, если файла ещё нет (можно создавать), иначе 1.
# Использование:  if create_if_missing "app/x.py"; then ... fi
create_if_missing() {
    local target="$1"
    if [ -e "$PROJECT_DIR/$target" ]; then
        log_warn "$target уже существует — пропускаю (режим 'не разрушать')"
        return 1
    fi
    return 0
}

# Создать директорию, если её нет.
ensure_dir() {
    local d="$1"
    mkdir -p "$PROJECT_DIR/$d"
}
LIBEOF
echo "  ✔ update_scripts/_lib.sh (общая библиотека)"

# Подключаем только что созданную библиотеку
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_lib.sh"

# ============================================================
# ЧАСТЬ 2: Каркас кластера (заготовки)
# ============================================================
echo ""
echo "🖧 Создаю каркас кластера (режим 'не разрушать')..."
echo ""

ensure_dir "app/cluster/roles"
ensure_dir "app/cluster/messaging"
ensure_dir "app/core"

# ---------- app/cluster/__init__.py ----------
if create_if_missing "app/cluster/__init__.py"; then
cat > "$PROJECT_DIR/app/cluster/__init__.py" << 'PYEOF'
# -*- coding: utf-8 -*-
"""
app/cluster
===========
Кластерная инфраструктура: узлы, роли, распределение камер.

ЗАГОТОВКА для будущего разделения серверов по задачам.
Сейчас всё работает на одном (локальном) узле.
"""
PYEOF
log_ok "app/cluster/__init__.py"
fi

# ---------- app/cluster/models.py ----------
if create_if_missing "app/cluster/models.py"; then
cat > "$PROJECT_DIR/app/cluster/models.py" << 'PYEOF'
# -*- coding: utf-8 -*-
"""
app/cluster/models.py
=====================
Модели кластера.

ЗАГОТОВКА:
  - Node             — узел кластера (имя, роль, адрес)
  - NodeRole         — роли серверов (разделение по задачам)
  - CameraAssignment — назначение камеры на узел захвата

Сейчас все камеры обрабатывает один локальный узел, но структура
уже готова к распределению по нескольким серверам.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeRole(str, Enum):
    """Роли серверов в кластере (разделение по задачам)."""
    CONTROL = "control"      # координация, конфиг, раздача фронтенда
    CAPTURE = "capture"      # захват потоков с камер
    RELAY = "relay"          # раздача HLS-фрагментов клиентам
    RECORDER = "recorder"    # запись в архив
    ANALYTICS = "analytics"  # детекция и аналитика


@dataclass
class Node:
    """Узел кластера."""
    id: str
    role: NodeRole
    host: str = "127.0.0.1"
    port: int = 5000
    enabled: bool = True
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["role"] = self.role.value
        return d

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["Node"]:
        if not isinstance(raw, dict):
            return None
        node_id = raw.get("id")
        if not node_id:
            return None
        try:
            role = NodeRole(raw.get("role", NodeRole.CAPTURE.value))
        except ValueError:
            role = NodeRole.CAPTURE
        return cls(
            id=str(node_id).strip(),
            role=role,
            host=str(raw.get("host", "127.0.0.1")).strip(),
            port=int(raw.get("port", 5000)),
            enabled=bool(raw.get("enabled", True)),
            tags=[str(t).strip() for t in raw.get("tags", [])],
        )


@dataclass
class CameraAssignment:
    """Назначение камеры на узел захвата."""
    camera_id: str
    node_id: str
    engine: str = "auto"  # ffmpeg / gstreamer / auto

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["CameraAssignment"]:
        if not isinstance(raw, dict):
            return None
        cam_id = raw.get("camera_id")
        node_id = raw.get("node_id")
        if not cam_id or not node_id:
            return None
        return cls(
            camera_id=str(cam_id).strip(),
            node_id=str(node_id).strip(),
            engine=str(raw.get("engine", "auto")).strip(),
        )
PYEOF
log_ok "app/cluster/models.py"
fi

# ---------- app/cluster/registry.py ----------
if create_if_missing "app/cluster/registry.py"; then
cat > "$PROJECT_DIR/app/cluster/registry.py" << 'PYEOF'
# -*- coding: utf-8 -*-
"""
app/cluster/registry.py
=======================
Реестр узлов кластера.

ЗАГОТОВКА: пока хранит один локальный узел. В будущем будет
поддерживать регистрацию нескольких узлов и проверку их живости.
"""
import logging
from typing import Dict, List, Optional

from app.cluster.models import Node, NodeRole

logger = logging.getLogger(__name__)


class NodeRegistry:
    """Реестр узлов кластера."""

    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._register_default()

    def _register_default(self) -> None:
        """Регистрирует локальный узел (пока всё на одном сервере)."""
        local = Node(
            id="local",
            role=NodeRole.CONTROL,
            host="127.0.0.1",
            port=5000,
            enabled=True,
            tags=["local", "all"],
        )
        self._nodes[local.id] = local
        logger.info("Зарегистрирован локальный узел: %s", local.id)

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def all_nodes(self) -> List[Node]:
        return list(self._nodes.values())

    def nodes_by_role(self, role: NodeRole) -> List[Node]:
        return [n for n in self._nodes.values() if n.role == role]

    def register(self, node: Node) -> None:
        self._nodes[node.id] = node
        logger.info("Зарегистрирован узел: %s (роль=%s)", node.id, node.role.value)

    def unregister(self, node_id: str) -> bool:
        if node_id in self._nodes:
            del self._nodes[node_id]
            return True
        return False


node_registry = NodeRegistry()
PYEOF
log_ok "app/cluster/registry.py"
fi

# ---------- app/cluster/scheduler.py ----------
if create_if_missing "app/cluster/scheduler.py"; then
cat > "$PROJECT_DIR/app/cluster/scheduler.py" << 'PYEOF'
# -*- coding: utf-8 -*-
"""
app/cluster/scheduler.py
========================
Распределение камер по узлам захвата.

ЗАГОТОВКА: пока все камеры назначаются на локальный узел.
В будущем будет балансировать нагрузку между несколькими
capture-узлами.
"""
import logging
from typing import Dict, List, Optional

from app.cluster.models import CameraAssignment

logger = logging.getLogger(__name__)


class CameraScheduler:
    """Распределяет камеры по узлам захвата."""

    def __init__(self):
        self._assignments: Dict[str, CameraAssignment] = {}

    def assign_all(self, camera_ids: List[str], node_id: str = "local") -> None:
        """Назначает все камеры на указанный узел."""
        for cam_id in camera_ids:
            self._assignments[cam_id] = CameraAssignment(
                camera_id=cam_id,
                node_id=node_id,
            )
        logger.info("Назначено %d камер на узел %s", len(camera_ids), node_id)

    def get_assignment(self, camera_id: str) -> Optional[CameraAssignment]:
        return self._assignments.get(camera_id)

    def cameras_on_node(self, node_id: str) -> List[str]:
        return [
            a.camera_id for a in self._assignments.values()
            if a.node_id == node_id
        ]


camera_scheduler = CameraScheduler()
PYEOF
log_ok "app/cluster/scheduler.py"
fi

# ---------- app/cluster/roles/base.py ----------
if create_if_missing "app/cluster/roles/__init__.py"; then
cat > "$PROJECT_DIR/app/cluster/roles/__init__.py" << 'PYEOF'
# -*- coding: utf-8 -*-
"""Роли серверов в кластере (разделение по задачам)."""
PYEOF
log_ok "app/cluster/roles/__init__.py"
fi

if create_if_missing "app/cluster/roles/base.py"; then
cat > "$PROJECT_DIR/app/cluster/roles/base.py" << 'PYEOF'
# -*- coding: utf-8 -*-
"""
app/cluster/roles/base.py
=========================
Базовый класс обработчика роли узла.

ЗАГОТОВКА: каждая роль (control, capture, relay, recorder,
analytics) реализует этот интерфейс и определяет, какие модули
активируются на сервере с данной ролью.
"""
from typing import Optional


class NodeRoleHandler:
    """Базовый обработчик роли узла."""

    #: Роль из NodeRole, которую обрабатывает этот класс
    role: Optional[str] = None

    def setup(self, app) -> None:
        """Инициализация роли при старте узла."""
        raise NotImplementedError

    def teardown(self) -> None:
        """Очистка при остановке узла."""
        pass
PYEOF
log_ok "app/cluster/roles/base.py"
fi

# ---------- app/cluster/messaging/bus.py ----------
if create_if_missing "app/cluster/messaging/__init__.py"; then
cat > "$PROJECT_DIR/app/cluster/messaging/__init__.py" << 'PYEOF'
# -*- coding: utf-8 -*-
"""Обмен сообщениями между узлами кластера."""
PYEOF
log_ok "app/cluster/messaging/__init__.py"
fi

if create_if_missing "app/cluster/messaging/bus.py"; then
cat > "$PROJECT_DIR/app/cluster/messaging/bus.py" << 'PYEOF'
# -*- coding: utf-8 -*-
"""
app/cluster/messaging/bus.py
============================
Шина событий кластера.

ЗАГОТОВКА: сейчас шина внутрипроцессная (pub/sub в памяти).
В будущем транспорт можно заменить на сетевой (очередь, HTTP),
не меняя подписчиков.

Это та же событийная шина, что используется для развязки модулей:
  - модули публикуют события (камера включена, поток потерян)
  - заинтересованные узлы/модули подписываются
"""
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class EventBus:
    """Простая шина событий (publish / subscribe)."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(payload)
            except Exception as e:  # noqa: BLE001
                logger.error("Ошибка обработчика события %s: %s", event_type, e)


cluster_bus = EventBus()
PYEOF
log_ok "app/cluster/messaging/bus.py"
fi

# ---------- app/core/node.py ----------
if create_if_missing "app/core/__init__.py"; then
cat > "$PROJECT_DIR/app/core/__init__.py" << 'PYEOF'
# -*- coding: utf-8 -*-
"""
app/core
========
Ядро приложения: конфигурация, идентификация узла, жизненный цикл.
"""
PYEOF
log_ok "app/core/__init__.py"
fi

if create_if_missing "app/core/node.py"; then
cat > "$PROJECT_DIR/app/core/node.py" << 'PYEOF'
# -*- coding: utf-8 -*-
"""
app/core/node.py
================
Идентификация текущего узла.

ЗАГОТОВКА: определяет, какой узел и с какой ролью запущен в
этом процессе. Позже будет читаться из конфигурации кластера
или аргументов командной строки (например, --role capture).
"""
import os
from typing import Optional


def current_node_id() -> str:
    """Идентификатор текущего узла (по умолчанию 'local')."""
    return os.environ.get("GRYPHONE_NODE_ID", "local")


def current_role() -> Optional[str]:
    """Роль текущего узла (пока не задана — единый сервер)."""
    return os.environ.get("GRYPHONE_NODE_ROLE")
PYEOF
log_ok "app/core/node.py"
fi

# ============================================================
# Проверка созданных файлов
# ============================================================
echo ""
echo "🔍 Проверка созданных файлов..."
for f in \
    "app/cluster/__init__.py" \
    "app/cluster/models.py" \
    "app/cluster/registry.py" \
    "app/cluster/scheduler.py" \
    "app/cluster/roles/__init__.py" \
    "app/cluster/roles/base.py" \
    "app/cluster/messaging/__init__.py" \
    "app/cluster/messaging/bus.py" \
    "app/core/__init__.py" \
    "app/core/node.py" \
    "update_scripts/_lib.sh"; do
    if [ ! -s "$PROJECT_DIR/$f" ]; then
        log_error "Файл $f пуст или не создан!"
        exit 1
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Фундамент кластера создан"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что создано:"
echo "  • update_scripts/_lib.sh — общая библиотека (определение Python)"
echo "  • app/cluster/          — узлы, роли, распределение, шина"
echo "  • app/core/node.py      — идентификация текущего узла"
echo ""
echo "ℹ️  Это ЗАГОТОВКИ. Они не меняют текущее поведение системы,"
echo "    но задают структуру для будущего разделения серверов."
echo ""
echo "🚀 Дальше (варианты):"
echo "  1. Подключить роли к create_app (запуск с --role)"
echo "  2. Продолжить модульный рефакторинг (этапы 1–4)"
echo "  3. Добавить поле engine в камеры (под GStreamer)"