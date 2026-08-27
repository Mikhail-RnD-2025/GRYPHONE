#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 19: ПОЛНОЦЕННАЯ СЕТКА КАМЕР
#  ------------------------------------------------------------
#  Что делает:
#    1. Обновляет app/routes/api.py: добавляет роут /api/sets/current
#       для получения камер активного набора.
#    2. Обновляет frontend/src/api.js: добавляет функцию
#       getCurrentSetCameras().
#    3. Обновляет frontend/src/pages/MonitorPage.jsx: загружает
#       камеры активного набора, учитывает max_columns и aspect_ratio.
#    4. Обновляет frontend/src/components/CameraCard.jsx: оптимизированный
#       плеер (создаётся только для доступных камер), обработка ошибок,
#       переключение main/sub по двойному клику.
#    5. Обновляет frontend/src/styles.css: стили адаптивной сетки.
#
#  Запуск:   bash 19_camera_grid.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. app/routes/api.py — добавлен роут /api/sets/current
# ============================================================
cat > "$PROJECT_DIR/app/routes/api.py" << 'PYEOF_API'
# -*- coding: utf-8 -*-
"""
app/routes/api.py
=================
Роуты ``/api/*``: управление камерами, наборами, конфигурацией, дашборд.

ДОБАВЛЕНО: роут /api/sets/current для получения камер активного набора
с информацией о настройках набора (max_columns, aspect_ratio).
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

        ДОБАВЛЕНО: этот роут нужен для сетки камер на фронтенде.
        Возвращает камеры только активного набора (не все камеры),
        а также настройки набора: имя, макс. колонок, макс. рядов,
        соотношение сторон.
        """
        current = camera_service.get_set(camera_service.current_set_id())
        cameras = camera_service.current_set_cameras()

        if not current:
            # Если набора нет, возвращаем все камеры с настройками по умолчанию.
            return jsonify({
                "set_id": "",
                "set_name": "Все камеры",
                "max_columns": 2,
                "max_rows": 0,
                "aspect_ratio": "16:9",
                "cameras": [c.to_dict() for c in camera_service.all_cameras()],
            })

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
echo "  ✔ app/routes/api.py (добавлен роут /api/sets/current)"

# ============================================================
# 2. frontend/src/api.js — добавлена функция getCurrentSetCameras
# ============================================================
cat > "$PROJECT_DIR/frontend/src/api.js" << 'JSEOF'
// ============================================================
//  GRYPHONE — клиент прикладного интерфейса
//  ------------------------------------------------------------
//  ДОБАВЛЕНО: функция getCurrentSetCameras() для получения камер
//  активного набора с информацией о настройках набора.
// ============================================================

const API_BASE = '/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`Ошибка запроса: ${response.status}`)
  }
  return response.json()
}

// ------------------------------------------------------------------
// Камеры
// ------------------------------------------------------------------
export function getCameras() {
  return request('/cameras')
}

export function saveCameras(cameras) {
  return request('/cameras/save', {
    method: 'POST',
    body: JSON.stringify({ cameras }),
  })
}

export function toggleCamera(camId, enabled) {
  return request('/cameras/toggle', {
    method: 'POST',
    body: JSON.stringify({ cam_id: camId, enabled }),
  })
}

export function updateComment(camId, comment) {
  return request('/cameras/comment', {
    method: 'POST',
    body: JSON.stringify({ cam_id: camId, comment }),
  })
}

// ------------------------------------------------------------------
// Наборы
// ------------------------------------------------------------------
export function getSets() {
  return request('/sets')
}

// ДОБАВЛЕНО: получение камер активного набора с настройками набора.
export function getCurrentSetCameras() {
  return request('/sets/current')
}

export function saveSets(data) {
  return request('/sets/save', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function switchSet(setId) {
  return request('/sets/switch', {
    method: 'POST',
    body: JSON.stringify({ set_id: setId }),
  })
}

// ------------------------------------------------------------------
// Конфигурация
// ------------------------------------------------------------------
export function getConfig() {
  return request('/config')
}

export function saveConfig(data) {
  return request('/config/save', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ------------------------------------------------------------------
// События
// ------------------------------------------------------------------
export function getEvents() {
  return request('/events')
}

export function publishEvent(event) {
  return request('/events/publish', {
    method: 'POST',
    body: JSON.stringify(event),
  })
}

// ------------------------------------------------------------------
// Дашборд
// ------------------------------------------------------------------
export function getDashboard() {
  return request('/dashboard')
}

// ------------------------------------------------------------------
// Логи
// ------------------------------------------------------------------
export function getFfmpegLogs() {
  return request('/ffmpeg_logs')
}
JSEOF
echo "  ✔ frontend/src/api.js (добавлена функция getCurrentSetCameras)"

# ============================================================
# 3. frontend/src/pages/MonitorPage.jsx — адаптивная сетка с наборами
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница мониторинга
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО:
//  - Загружает камеры активного набора (не все камеры).
//  - Учитывает настройки набора: имя, макс. колонок, соотношение сторон.
//  - Отображает имя набора в шапке.
// ============================================================
import { useState, useEffect } from 'react'
import Header from '../components/Header'
import CameraCard from '../components/CameraCard'
import ContextMenu from '../components/ContextMenu'
import Toasts from '../components/Toasts'
import useStreamStatus from '../hooks/useStreamStatus'
import { getCurrentSetCameras } from '../api'

export default function MonitorPage() {
  // Данные активного набора: камеры и настройки.
  const [setData, setSetData] = useState(null)
  // Список камер активного набора.
  const [cameras, setCameras] = useState([])
  // Состояние контекстного меню.
  const [contextMenu, setContextMenu] = useState(null)

  // Подписка на события в реальном времени (статусы потоков).
  const stats = useStreamStatus()

  // Загружаем камеры активного набора при монтировании.
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
    // Если в наборе задано макс. колонок — используем фиксированную сетку.
    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, 1fr)`
  } else {
    // Иначе — адаптивная сетка.
    gridStyle.gridTemplateColumns = 'repeat(auto-fill, minmax(300px, 1fr))'
  }

  return (
    <div className="page">
      {/* Шапка страницы */}
      <Header />

      {/* Информация о наборе */}
      {setData && (
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

      {/* Сетка камер */}
      <div style={gridStyle}>
        {cameras.map((camera) => {
          // Статус хранится по ключу {camera.id}_main.
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

      {/* Если камер нет */}
      {cameras.length === 0 && (
        <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
          В активном наборе нет камер. Добавьте камеры через Настройки.
        </div>
      )}

      {/* Контекстное меню (если открыто) */}
      {contextMenu && (
        <ContextMenu
          camera={contextMenu.camera}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={handleCloseContextMenu}
          onUpdate={loadCurrentSet}
        />
      )}

      {/* Уведомления */}
      <Toasts />
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/MonitorPage.jsx (адаптивная сетка с наборами)"

# ============================================================
# 4. frontend/src/components/CameraCard.jsx — оптимизированный плеер
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/CameraCard.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — компонент «Карточка камеры»
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО:
//  - Плеер создаётся только для камер со статусом "в_сети" или
//    "подключение", не создаётся для выключенных и недоступных.
//  - Обрабатываются ошибки загрузки (показывается сообщение).
//  - Переключение между потоками (основной/дополнительный) по
//    двойному клику.
//  - Выключенные камеры показывают статус "Отключена".
// ============================================================
import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'

export default function CameraCard({ camera, status, aspectRatio, onContextMenu }) {
  // Ссылка на элемент видео.
  const videoRef = useRef(null)
  // Экземпляр плеера.
  const hlsRef = useRef(null)
  // Тип потока: 'основной' или 'дополнительный'.
  const [streamType, setStreamType] = useState('основной')
  // Ошибка загрузки потока.
  const [error, setError] = useState(null)

  // Идентификатор потока для запроса сегментов.
  const routeId = `${camera.id}_${streamType}`
  const streamUrl = `/hls/camera/${routeId}/index.m3u8`

  // Создаём плеер только если камера включена и статус не "недоступна".
  const shouldPlay = camera.enabled && status !== 'недоступна'

  // Инициализация плеера при монтировании и при изменении потока.
  useEffect(() => {
    // Если камера выключена или недоступна — не создаём плеер.
    if (!shouldPlay || !videoRef.current) return

    setError(null)

    if (Hls.isSupported()) {
      const hls = new Hls()
      hls.loadSource(streamUrl)
      hls.attachMedia(videoRef.current)

      // Когда плейлист загружен — начинаем воспроизведение.
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        videoRef.current.play().catch(() => {})
      })

      // Обработка ошибок загрузки.
      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          setError('Поток недоступен')
          hls.destroy()
          hlsRef.current = null
        }
      })

      hlsRef.current = hls
    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      // Для браузеров с нативной поддержкой формата.
      videoRef.current.src = streamUrl
      videoRef.current.play().catch(() => setError('Не удалось воспроизвести'))
    }

    // При размонтировании очищаем плеер.
    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
    }
  }, [streamUrl, shouldPlay])

  // Переключение между потоками по двойному клику.
  const handleDoubleClick = () => {
    // Переключаем только если есть дополнительный поток.
    if (camera.sub_url && camera.sub_url !== camera.main_url) {
      setStreamType(prev => prev === 'основной' ? 'дополнительный' : 'основной')
    }
  }

  // Определяем класс статуса для отображения.
  const getStatusBadge = () => {
    if (!camera.enabled) return { text: 'Отключена', cls: 'status-offline' }
    if (status === 'в_сети') return { text: 'Онлайн', cls: 'status-online' }
    if (status === 'недоступна') return { text: 'Недоступна', cls: 'status-offline' }
    return { text: 'Подключение', cls: 'status-connecting' }
  }

  const badge = getStatusBadge()

  // Вычисляем соотношение сторон для видео.
  const aspectStyle = aspectRatio === '4:3' ? '75%' : '56.25%'

  return (
    <div
      className="camera-card"
      onContextMenu={(e) => {
        e.preventDefault()
        if (onContextMenu) onContextMenu(camera, e.clientX, e.clientY)
      }}
      onDoubleClick={handleDoubleClick}
    >
      {/* Имя камеры и статус */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="camera-name">{camera.name}</span>
        <span className={`status-badge ${badge.cls}`}>{badge.text}</span>
      </div>

      {/* Область видео с соотношением сторон */}
      <div style={{
        position: 'relative', width: '100%',
        paddingTop: aspectStyle, marginTop: '8px',
        background: '#0b0d10', borderRadius: '4px', overflow: 'hidden',
      }}>
        {camera.enabled && (
          <video
            ref={videoRef}
            muted
            playsInline
            style={{
              position: 'absolute', top: 0, left: 0,
              width: '100%', height: '100%', objectFit: 'contain',
            }}
          />
        )}

        {/* Сообщение об ошибке */}
        {error && (
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#dc2626', fontSize: '0.875rem', textAlign: 'center',
          }}>
            {error}
          </div>
        )}

        {/* Сообщение для выключенной камеры */}
        {!camera.enabled && (
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#94a3b8', fontSize: '0.875rem', textAlign: 'center',
          }}>
            Камера отключена
          </div>
        )}
      </div>

      {/* Метрики (если есть) */}
      {status === 'в_сети' && (
        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '4px' }}>
          {streamType === 'основной' ? 'Основной поток' : 'Дополнительный поток'}
        </div>
      )}
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/components/CameraCard.jsx (оптимизированный плеер)"

# ============================================================
# 5. frontend/src/styles.css — добавлены стили адаптивной сетки
# ============================================================
cat > "$PROJECT_DIR/frontend/src/styles.css" << 'CSSEOF'
/* ============================================================
   GRYPHONE — стили приложения
   ------------------------------------------------------------
   ДОБАВЛЕНО: стили для адаптивной сетки камер, статусов,
   карточек камер.
   ============================================================ */

/* Сброс отступов и базовые настройки */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #0b0d10;
  color: #e0e3e8;
  min-height: 100vh;
}

/* Контейнер страницы */
.page {
  padding: 16px;
  max-width: 1400px;
  margin: 0 auto;
}

/* Заголовок страницы */
.page-title {
  font-size: 1.5rem;
  margin-bottom: 16px;
}

/* Шапка приложения */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #1e293b;
}

.header-title {
  font-size: 1.25rem;
  color: #2563eb;
}

.header-clock {
  font-size: 0.875rem;
  color: #94a3b8;
}

/* Карточка камеры */
.camera-card {
  background: #1e293b;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #334155;
  transition: border-color 0.2s ease;
}

.camera-card:hover {
  border-color: #2563eb;
}

.camera-name {
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Статус камеры */
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  white-space: nowrap;
}
.status-online {
  background: #059669;
  color: #fff;
}
.status-offline {
  background: #dc2626;
  color: #fff;
}
.status-connecting {
  background: #d97706;
  color: #fff;
}

/* Кнопки */
.btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  background: #334155;
  color: #e0e3e8;
}
.btn:hover {
  background: #475569;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
}
.btn-primary:hover {
  background: #1d4ed8;
}
.btn-danger {
  background: #dc2626;
  color: #fff;
}
.btn-danger:hover {
  background: #b91c1c;
}

/* Уведомления */
.toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.toast {
  padding: 12px 16px;
  border-radius: 6px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
.toast-success {
  background: #059669;
}
.toast-error {
  background: #dc2626;
}
.toast-info {
  background: #2563eb;
}

/* Контекстное меню */
.context-menu {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  min-width: 200px;
}

.context-menu .btn {
  width: 100%;
  margin-bottom: 8px;
}

.context-menu textarea {
  background: #0b0d10;
  color: #e0e3e8;
  border: 1px solid #334155;
  border-radius: 4px;
  padding: 8px;
  font-size: 0.875rem;
  resize: vertical;
}
CSSEOF
echo "  ✔ frontend/src/styles.css (стили адаптивной сетки)"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in app/routes/api.py frontend/src/api.js frontend/src/pages/MonitorPage.jsx frontend/src/components/CameraCard.jsx frontend/src/styles.css; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Сетка камер реализована"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что теперь в сетке камер:"
echo "  • Загружаются камеры только активного набора"
echo "  • Учитываются настройки набора: макс. колонок, соотношение сторон"
echo "  • Плеер создаётся только для доступных камер"
echo "  • Обрабатываются ошибки загрузки потока"
echo "  • Выключенные камеры показывают статус 'Отключена'"
echo "  • Двойной клик — переключение основной/дополнительный поток"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000"