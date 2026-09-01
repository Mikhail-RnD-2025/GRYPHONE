#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 20: ПУСТЫЕ НАБОРЫ
#  ------------------------------------------------------------
#  Исправляет поведение: если наборы не созданы, бэкенд
#  возвращает пустой список камер, а фронтенд показывает
#  сообщение «Наборы не созданы».
#
#  Что делает:
#    1. Обновляет app/routes/api.py: роут /api/sets/current
#       возвращает пустой список, если набора нет.
#    2. Обновляет frontend/src/pages/MonitorPage.jsx: показывает
#       сообщение и кнопку перехода в настройки.
#
#  Запуск:   bash 20_empty_sets.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. app/routes/api.py — исправлен роут /api/sets/current
# ============================================================
cat > "$PROJECT_DIR/app/routes/api.py" << 'PYEOF_API'
# -*- coding: utf-8 -*-
"""
app/routes/api.py
=================
Роуты ``/api/*``: управление камерами, наборами, конфигурацией, дашборд.

ИСПРАВЛЕНО: роут /api/sets/current возвращает пустой список камер,
если наборы не созданы (ранее возвращал все камеры).
"""
import logging
from flask import jsonify, request

from app.config import config
from app.models import Event
from app.services.camera_service import camera_service
from app.services.stream_manager import stream_manager
from app.services.config_sync import config_sync

logger = logging.getLogger(__name__)


def _collect_system_stats() -> dict:
    """Собирает статистику системных ресурсов."""
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu": round(cpu_percent, 1),
            "ram": round(memory.percent, 1),
            "ram_used_gb": round(memory.used / (1024 ** 3), 2),
            "ram_total_gb": round(memory.total / (1024 ** 3), 2),
            "disk": round(disk.percent, 1),
            "disk_used_gb": round(disk.used / (1024 ** 3), 2),
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        }
    except ImportError:
        logger.warning("⚠️ Модуль мониторинга не установлен")
        return {
            "cpu": 0, "ram": 0, "ram_used_gb": 0, "ram_total_gb": 0,
            "disk": 0, "disk_used_gb": 0, "disk_total_gb": 0,
        }


def _collect_camera_stats() -> tuple:
    """Собирает статистику по камерам и потокам."""
    cameras = camera_service.all_cameras()
    stats = stream_manager.get_all_stats()

    total_cameras = len(cameras)
    enabled_cameras = sum(1 for c in cameras if c.enabled)
    online_streams = 0
    offline_streams = 0
    connecting_streams = 0
    camera_details = []

    for cam in cameras:
        route_id = cam.main_route_id
        status = stats.get(route_id, {})
        state = status.get("state", "подключение")

        if state == "в_сети":
            online_streams += 1
        elif state == "недоступна":
            offline_streams += 1
        else:
            connecting_streams += 1

        camera_details.append({
            "id": cam.id,
            "name": cam.name,
            "enabled": cam.enabled,
            "state": state,
            "msg": status.get("msg", ""),
            "metrics": status.get("metrics", {}),
        })

    summary = {
        "total_cameras": total_cameras,
        "enabled_cameras": enabled_cameras,
        "disabled_cameras": total_cameras - enabled_cameras,
        "online_streams": online_streams,
        "offline_streams": offline_streams,
        "connecting_streams": connecting_streams,
    }
    return summary, camera_details


def register(app):
    """Регистрирует роуты ``/api/*`` в приложении."""

    # ------------------------------------------------------------------
    # Камеры
    # ------------------------------------------------------------------
    @app.route("/api/cameras", methods=["GET"])
    def get_cameras():
        """Возвращает список всех камер."""
        cameras = camera_service.all_cameras()
        return jsonify([c.to_dict() for c in cameras])

    @app.route("/api/cameras/save", methods=["POST"])
    def save_cameras():
        """Сохраняет список камер из запроса."""
        data = request.get_json()
        if not data or "cameras" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        saved = camera_service.save_cameras(data["cameras"])
        config_sync.sync_cameras(camera_service.all_cameras())
        return jsonify({"success": True, "saved": saved})

    @app.route("/api/cameras/toggle", methods=["POST"])
    def toggle_camera():
        """Включает/выключает камеру."""
        data = request.get_json()
        if not data or "cam_id" not in data or "enabled" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        cam = camera_service.toggle_camera(data["cam_id"], data["enabled"])
        if not cam:
            return jsonify({"success": False, "msg": "Камера не найдена"}), 404
        return jsonify({"success": True, "camera": cam.to_dict()})

    @app.route("/api/cameras/comment", methods=["POST"])
    def update_comment():
        """Обновляет комментарий камеры."""
        data = request.get_json()
        if not data or "cam_id" not in data or "comment" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        cam = camera_service.update_comment(data["cam_id"], data["comment"])
        if not cam:
            return jsonify({"success": False, "msg": "Камера не найдена"}), 404
        return jsonify({"success": True, "camera": cam.to_dict()})

    # ------------------------------------------------------------------
    # Наборы
    # ------------------------------------------------------------------
    @app.route("/api/sets", methods=["GET"])
    def get_sets():
        """Возвращает все наборы камер."""
        sets = camera_service.all_sets()
        return jsonify({
            "default_set": camera_service.default_set_id(),
            "sets": {s_id: s.to_dict() for s_id, s in sets.items()},
        })

    @app.route("/api/sets/current", methods=["GET"])
    def get_current_set():
        """Возвращает камеры активного набора и информацию о наборе.

        ИСПРАВЛЕНО: если наборы не созданы, возвращает пустой список
        камер (ранее возвращал все камеры).
        """
        current = camera_service.get_set(camera_service.current_set_id())

        # Если набора нет — возвращаем пустой список камер.
        if not current:
            return jsonify({
                "set_id": "",
                "set_name": "",
                "max_columns": 0,
                "max_rows": 0,
                "aspect_ratio": "16:9",
                "cameras": [],
            })

        cameras = camera_service.current_set_cameras()
        return jsonify({
            "set_id": current.id,
            "set_name": current.name,
            "max_columns": current.max_columns,
            "max_rows": current.max_rows,
            "aspect_ratio": current.aspect_ratio,
            "cameras": [c.to_dict() for c in cameras],
        })

    @app.route("/api/sets/save", methods=["POST"])
    def save_sets():
        """Сохраняет наборы из запроса."""
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        ok = camera_service.save_sets(data)
        if not ok:
            return jsonify({"success": False, "msg": "Неверный формат"}), 400
        return jsonify({"success": True})

    @app.route("/api/sets/switch", methods=["POST"])
    def switch_set():
        """Переключает активный набор."""
        data = request.get_json()
        if not data or "set_id" not in data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        ok = camera_service.switch_set(data["set_id"])
        if not ok:
            return jsonify({"success": False, "msg": "Набор не найден"}), 404
        return jsonify({"success": True})

    # ------------------------------------------------------------------
    # Конфигурация
    # ------------------------------------------------------------------
    @app.route("/api/config", methods=["GET"])
    def get_config():
        """Возвращает текущую конфигурацию."""
        return jsonify(config.all())

    @app.route("/api/config/save", methods=["POST"])
    def save_config():
        """Сохраняет конфигурацию из запроса."""
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        config.save()
        return jsonify({"success": True})

    # ------------------------------------------------------------------
    # События
    # ------------------------------------------------------------------
    @app.route("/api/events", methods=["GET"])
    def get_events():
        """Возвращает список событий."""
        return jsonify([])

    @app.route("/api/events/publish", methods=["POST"])
    def publish_event():
        """Публикует событие."""
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Нет данных"}), 400
        event = Event.make(
            source=data.get("source", "system"),
            event_type=data.get("event_type", "unknown"),
            severity=data.get("severity", "info"),
            camera_id=data.get("camera_id"),
            payload=data.get("payload", {}),
        )
        config_sync.publish_event(event)
        return jsonify({"success": True, "event": event.to_dict()})

    # ------------------------------------------------------------------
    # Дашборд
    # ------------------------------------------------------------------
    @app.route("/api/dashboard", methods=["GET"])
    def dashboard():
        """Возвращает данные для дашборда."""
        system = _collect_system_stats()
        stats_summary, camera_details = _collect_camera_stats()
        return jsonify({
            "system": system,
            "stats": stats_summary,
            "cameras": camera_details,
        })
PYEOF_API
echo "  ✔ app/routes/api.py (исправлен роут /api/sets/current)"

# ============================================================
# 2. frontend/src/pages/MonitorPage.jsx — сообщение «Наборы не созданы»
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница мониторинга
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО: если наборы не созданы, показывается сообщение
//  «Наборы не созданы» и кнопка перехода в настройки.
// ============================================================
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import Header from '../components/Header'
import CameraCard from '../components/CameraCard'
import ContextMenu from '../components/ContextMenu'
import Toasts from '../components/Toasts'
import useStreamStatus from '../hooks/useStreamStatus'
import { getCurrentSetCameras } from '../api'

export default function MonitorPage() {
  const [setData, setSetData] = useState(null)
  const [cameras, setCameras] = useState([])
  const [contextMenu, setContextMenu] = useState(null)

  const stats = useStreamStatus()

  useEffect(() => {
    loadCurrentSet()
  }, [])

  const loadCurrentSet = async () => {
    try {
      const data = await getCurrentSetCameras()
      setSetData(data)
      setCameras(data.cameras || [])
    } catch (e) {
      console.error('Ошибка загрузки камер набора:', e)
    }
  }

  const handleContextMenu = (camera, x, y) => {
    setContextMenu({ camera, x, y })
  }

  const handleCloseContextMenu = () => {
    setContextMenu(null)
  }

  // Вычисляем стиль сетки на основе настроек набора.
  const gridStyle = {
    display: 'grid',
    gap: '12px',
  }

  if (setData && setData.max_columns > 0) {
    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, 1fr)`
  } else {
    gridStyle.gridTemplateColumns = 'repeat(auto-fill, minmax(300px, 1fr))'
  }

  // Определяем, что показать, если камер нет.
  const hasSets = setData && setData.set_id !== ''

  return (
    <div className="page">
      <Header />

      {/* Информация о наборе (только если набор существует) */}
      {hasSets && (
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: '12px',
        }}>
          <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
            Набор: <strong style={{ color: '#e0e3e8' }}>{setData.set_name}</strong>
            {' '}• Камер: {cameras.length}
          </span>
        </div>
      )}

      {/* Сетка камер (только если набор существует и есть камеры) */}
      {hasSets && cameras.length > 0 && (
        <div style={gridStyle}>
          {cameras.map((camera) => {
            const routeId = camera.id + '_main'
            const status = stats[routeId]?.state || 'подключение'
            return (
              <CameraCard
                key={camera.id}
                camera={camera}
                status={status}
                aspectRatio={setData?.aspect_ratio || '16:9'}
                onContextMenu={handleContextMenu}
              />
            )
          })}
        </div>
      )}

      {/* Сообщение: наборы не созданы */}
      {!hasSets && (
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          background: '#1e293b', borderRadius: '8px',
          border: '1px dashed #334155',
        }}>
          <div style={{ fontSize: '1.25rem', marginBottom: '12px' }}>
            📹 Наборы не созданы
          </div>
          <div style={{ color: '#94a3b8', marginBottom: '20px' }}>
            Для начала работы создайте набор камер и добавьте в него камеры.
          </div>
          <Link to="/settings" className="btn btn-primary">
            Перейти в настройки
          </Link>
        </div>
      )}

      {/* Сообщение: набор существует, но камер в нём нет */}
      {hasSets && cameras.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          background: '#1e293b', borderRadius: '8px',
          border: '1px dashed #334155',
        }}>
          <div style={{ fontSize: '1.25rem', marginBottom: '12px' }}>
            📹 В наборе «{setData.set_name}» нет камер
          </div>
          <div style={{ color: '#94a3b8', marginBottom: '20px' }}>
            Добавьте камеры в этот набор через настройки.
          </div>
          <Link to="/settings" className="btn btn-primary">
            Перейти в настройки
          </Link>
        </div>
      )}

      {/* Контекстное меню */}
      {contextMenu && (
        <ContextMenu
          camera={contextMenu.camera}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={handleCloseContextMenu}
          onUpdate={loadCurrentSet}
        />
      )}

      <Toasts />
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/MonitorPage.jsx (сообщение «Наборы не созданы»)"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in app/routes/api.py frontend/src/pages/MonitorPage.jsx; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Исправление применено"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что изменилось:"
echo "  • Если наборы не созданы → бэкенд возвращает пустой список камер"
echo "  • Фронтенд показывает: «Наборы не созданы» + кнопка в настройки"
echo "  • Если набор есть, но пустой → «В наборе нет камер» + кнопка"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000"