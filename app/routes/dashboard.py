# -*- coding: utf-8 -*-
"""
app/routes/dashboard.py
=======================
Улучшенный дашборд с детальной статистикой системы.

Endpoint:
  GET /api/dashboard

Возвращает:
  - total_cameras: общее количество камер
  - enabled_cameras: включённые камеры
  - disabled_cameras: выключенные камеры
  - online_streams: потоки в сети
  - offline_streams: потоки не в сети
  - connecting_streams: потоки в процессе подключения
  - system: нагрузка системы (CPU, RAM, диск, сеть)
  - sets: статистика по наборам
  - problem_cameras: список проблемных камер
  - recent_events: последние события
"""
import logging
import time
import platform
from pathlib import Path
from flask import jsonify

from app.config import config
from app.services.camera_service import camera_service
from app.services.stream_manager import stream_manager

logger = logging.getLogger(__name__)

# Хранилище последних событий (в памяти, максимум 100)
_recent_events = []


def add_event(event_type: str, message: str, severity: str = "info", camera_id: str = None):
    """Добавляет событие в лог последних событий."""
    global _recent_events
    _recent_events.append({
        'timestamp': time.time(),
        'type': event_type,
        'message': message,
        'severity': severity,
        'camera_id': camera_id,
    })
    # Ограничиваем до 100 событий
    if len(_recent_events) > 100:
        _recent_events = _recent_events[-100:]


def get_system_stats() -> dict:
    """
    Собирает статистику нагрузки системы.

    Использует библиотеку psutil если доступна,
    иначе возвращает заглушки.
    """
    try:
        import psutil

        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()

        # Память
        memory = psutil.virtual_memory()

        # Диск
        disk = psutil.disk_usage('/')

        # Сеть (если доступна)
        try:
            net = psutil.net_io_counters()
            net_stats = {
                'bytes_sent': net.bytes_sent,
                'bytes_recv': net.bytes_recv,
                'packets_sent': net.packets_sent,
                'packets_recv': net.packets_recv,
            }
        except Exception:
            net_stats = {
                'bytes_sent': 0,
                'bytes_recv': 0,
                'packets_sent': 0,
                'packets_recv': 0,
            }

        return {
            'cpu_percent': round(cpu_percent, 1),
            'cpu_count': cpu_count,
            'memory_percent': round(memory.percent, 1),
            'memory_used_mb': round(memory.used / (1024 * 1024), 1),
            'memory_total_mb': round(memory.total / (1024 * 1024), 1),
            'memory_available_mb': round(memory.available / (1024 * 1024), 1),
            'disk_percent': round(disk.percent, 1),
            'disk_used_gb': round(disk.used / (1024 ** 3), 2),
            'disk_total_gb': round(disk.total / (1024 ** 3), 2),
            'disk_free_gb': round(disk.free / (1024 ** 3), 2),
            'network': net_stats,
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'uptime': round(time.time() - psutil.boot_time(), 0),
        }
    except ImportError:
        logger.warning("psutil не установлен, статистика системы недоступна")
        return {
            'cpu_percent': 0,
            'cpu_count': 0,
            'memory_percent': 0,
            'memory_used_mb': 0,
            'memory_total_mb': 0,
            'memory_available_mb': 0,
            'disk_percent': 0,
            'disk_used_gb': 0,
            'disk_total_gb': 0,
            'disk_free_gb': 0,
            'network': {},
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'uptime': 0,
        }
    except Exception as e:
        logger.error(f"Ошибка получения статистики системы: {e}")
        return {
            'cpu_percent': 0,
            'cpu_count': 0,
            'memory_percent': 0,
            'memory_used_mb': 0,
            'memory_total_mb': 0,
            'memory_available_mb': 0,
            'disk_percent': 0,
            'disk_used_gb': 0,
            'disk_total_gb': 0,
            'disk_free_gb': 0,
            'network': {},
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'uptime': 0,
        }


def get_camera_stats() -> dict:
    """Собирает статистику по камерам."""
    cameras = camera_service.all_cameras()
    stats = stream_manager.get_all_stats()

    total = len(cameras)
    enabled = sum(1 for c in cameras if c.enabled)
    disabled = total - enabled

    online = 0
    offline = 0
    connecting = 0

    for cam in cameras:
        route_id = cam.main_route_id
        status = stats.get(route_id, {})
        state = status.get('state', 'подключение')

        if state == 'в_сети':
            online += 1
        elif state == 'недоступна':
            offline += 1
        else:
            connecting += 1

    return {
        'total': total,
        'enabled': enabled,
        'disabled': disabled,
        'online': online,
        'offline': offline,
        'connecting': connecting,
    }


def get_problem_cameras(limit: int = 20) -> list:
    """
    Возвращает список проблемных камер.

    Проблемные камеры:
      - Включены, но поток не в сети
      - Имеют ошибки подключения
    """
    cameras = camera_service.all_cameras()
    stats = stream_manager.get_all_stats()

    problems = []
    for cam in cameras:
        if not cam.enabled:
            continue

        route_id = cam.main_route_id
        status = stats.get(route_id, {})
        state = status.get('state', 'подключение')

        # Проблемная если включена, но не в сети
        if state != 'в_сети':
            problems.append({
                'id': cam.id,
                'name': cam.name,
                'location': cam.location,
                'state': state,
                'message': status.get('msg', ''),
                'enabled': cam.enabled,
            })

    # Сортируем по состоянию (недоступна сначала)
    problems.sort(key=lambda x: 0 if x['state'] == 'недоступна' else 1)

    return problems[:limit]


def get_sets_stats() -> list:
    """Возвращает статистику по наборам."""
    sets = camera_service.all_sets()
    stats = stream_manager.get_all_stats()

    result = []
    for set_id, set_data in sets.items():
        cam_ids = set_data.camera_ids
        online = 0
        offline = 0

        for cam_id in cam_ids:
            cam = camera_service.get_camera(cam_id)
            if cam and cam.enabled:
                route_id = cam.main_route_id
                status = stats.get(route_id, {})
                if status.get('state') == 'в_сети':
                    online += 1
                else:
                    offline += 1

        result.append({
            'id': set_id,
            'name': set_data.name,
            'total_cameras': len(cam_ids),
            'online': online,
            'offline': offline,
            'max_columns': set_data.max_columns,
            'max_rows': set_data.max_rows,
        })

    return result


def register(app):
    """Регистрирует роуты дашборда."""

    @app.route("/api/dashboard", methods=["GET"])
    def dashboard():
        """
        Улучшенный дашборд с детальной статистикой.

        Возвращает:
          - cameras: статистика камер
          - system: нагрузка системы
          - sets: статистика по наборам
          - problem_cameras: проблемные камеры
          - recent_events: последние события
        """
        camera_stats = get_camera_stats()
        system_stats = get_system_stats()
        sets_stats = get_sets_stats()
        problem_cameras = get_problem_cameras()

        return jsonify({
            'cameras': camera_stats,
            'system': system_stats,
            'sets': sets_stats,
            'problem_cameras': problem_cameras,
            'recent_events': _recent_events[-20:],  # Последние 20 событий
            'timestamp': time.time(),
        })

    @app.route("/api/dashboard/events", methods=["GET"])
    def dashboard_events():
        """Возвращает последние события."""
        from flask import request
        limit = request.args.get('limit', 50, type=int)
        return jsonify({
            'events': _recent_events[-limit:],
            'total': len(_recent_events),
        })
