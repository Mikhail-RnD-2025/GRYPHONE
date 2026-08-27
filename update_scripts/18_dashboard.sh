#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 18: ПОЛНОЦЕННЫЙ ДАШБОРД
#  ------------------------------------------------------------
#  Что делает:
#    1. Обновляет app/routes/api.py: роут /api/dashboard собирает
#       реальную статистику (система, камеры, потоки).
#    2. Обновляет frontend/src/pages/SettingsPage.jsx: визуальный
#       дашборд с карточками, прогресс-барами и таблицей камер.
#       Автообновление каждые 3 секунды.
#
#  Запуск:   bash 18_dashboard.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. app/routes/api.py — полноценный роут /api/dashboard
# ============================================================
cat > "$PROJECT_DIR/app/routes/api.py" << 'PYEOF_API'
# -*- coding: utf-8 -*-
"""
app/routes/api.py
=================
Роуты ``/api/*``: управление камерами, наборами, конфигурацией, дашборд.

ИСПРАВЛЕНО: роут /api/dashboard собирает реальную статистику
из трёх источников:
  - системные ресурсы (через сторонний модуль мониторинга);
  - камеры и наборы (через сервис камер);
  - статусы потоков (через менеджер стримера).
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
    """Собирает статистику системных ресурсов.

    Возвращает словарь с загрузкой процессора, памяти и диска.
    Если сторонний модуль недоступен, возвращает нули.
    """
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
    """Собирает статистику по камерам и потокам.

    Возвращает кортеж ``(сводка, список_камер)``.
    """
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
    # Дашборд (полноценная реализация)
    # ------------------------------------------------------------------
    @app.route("/api/dashboard", methods=["GET"])
    def dashboard():
        """Возвращает данные для дашборда.

        Собирает статистику из трёх источников:
          - системные ресурсы (через модуль мониторинга);
          - камеры (через сервис камер);
          - потоки (через менеджер стримера).
        """
        system = _collect_system_stats()
        stats_summary, camera_details = _collect_camera_stats()

        return jsonify({
            "system": system,
            "stats": stats_summary,
            "cameras": camera_details,
        })
PYEOF_API
echo "  ✔ app/routes/api.py (полноценный роут /api/dashboard)"

# ============================================================
# 2. frontend/src/pages/SettingsPage.jsx — визуальный дашборд
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/SettingsPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница настроек
//  ------------------------------------------------------------
//  Вкладки: конфигурация, камеры, наборы, логи, дашборд.
//  ИСПРАВЛЕНО: дашборд теперь визуальный, с карточками,
//  прогресс-барами и таблицей камер. Автообновление каждые 3 секунды.
// ============================================================
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getConfig, getCameras, getSets, getFfmpegLogs, getDashboard } from '../api'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [config, setConfig] = useState({})
  const [cameras, setCameras] = useState([])
  const [sets, setSets] = useState({})
  const [logs, setLogs] = useState({})
  const [dashboard, setDashboard] = useState(null)

  // Загружаем данные при монтировании.
  useEffect(() => {
    loadData()
  }, [])

  // Автообновление дашборда каждые 3 секунды, когда вкладка активна.
  useEffect(() => {
    if (activeTab !== 'dashboard') return
    const timer = setInterval(() => {
      loadDashboard()
    }, 3000)
    return () => clearInterval(timer)
  }, [activeTab])

  const loadData = async () => {
    try {
      const [cfg, cams, sts] = await Promise.all([
        getConfig(),
        getCameras(),
        getSets(),
      ])
      setConfig(cfg)
      setCameras(cams)
      setSets(sts)
      await loadDashboard()
    } catch (e) {
      console.error('Ошибка загрузки данных:', e)
    }
  }

  const loadDashboard = async () => {
    try {
      const data = await getDashboard()
      setDashboard(data)
    } catch (e) {
      console.error('Ошибка загрузки дашборда:', e)
    }
  }

  const loadLogs = async () => {
    try {
      const data = await getFfmpegLogs()
      setLogs(data)
    } catch (e) {
      console.error('Ошибка загрузки логов:', e)
    }
  }

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    if (tab === 'logs') loadLogs()
  }

  // Вспомогательный компонент: прогресс-бар.
  const ProgressBar = ({ value, color }) => {
    const barColor = value > 80 ? '#dc2626' : value > 60 ? '#d97706' : color || '#2563eb'
    return (
      <div style={{
        width: '100%', height: '8px', background: '#1e293b',
        borderRadius: '4px', overflow: 'hidden',
      }}>
        <div style={{
          width: `${value}%`, height: '100%', background: barColor,
          transition: 'width 0.3s ease',
        }} />
      </div>
    )
  }

  // Вспомогательный компонент: карточка метрики.
  const MetricCard = ({ title, value, unit, bar }) => (
    <div className="camera-card" style={{ minWidth: '200px' }}>
      <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>{title}</div>
      <div style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: '8px 0' }}>
        {value} <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>{unit}</span>
      </div>
      {bar !== undefined && <ProgressBar value={bar} />}
    </div>
  )

  // Определяем цвет и текст статуса камеры.
  const getStatusBadge = (state) => {
    if (state === 'в_сети') return { text: 'Онлайн', cls: 'status-online' }
    if (state === 'недоступна') return { text: 'Офлайн', cls: 'status-offline' }
    return { text: 'Подключение', cls: 'status-connecting' }
  }

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 className="page-title">Настройки</h1>
        <Link to="/" className="btn btn-primary">Назад к мониторингу</Link>
      </div>

      {/* Вкладки */}
      <div className="tabs" style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
        {['dashboard', 'config', 'cameras', 'sets', 'logs'].map((tab) => (
          <button
            key={tab}
            className={`btn ${activeTab === tab ? 'btn-primary' : ''}`}
            onClick={() => handleTabChange(tab)}
          >
            {tab === 'dashboard' && 'Дашборд'}
            {tab === 'config' && 'Конфигурация'}
            {tab === 'cameras' && 'Камеры'}
            {tab === 'sets' && 'Наборы'}
            {tab === 'logs' && 'Логи'}
          </button>
        ))}
      </div>

      {/* Содержимое активной вкладки */}
      <div className="tab-content">

        {/* ---------- ДАШБОРД ---------- */}
        {activeTab === 'dashboard' && dashboard && (
          <div>
            <h2 style={{ marginBottom: '16px' }}>Дашборд</h2>

            {/* Системные ресурсы */}
            <h3 style={{ margin: '16px 0 8px' }}>Системные ресурсы</h3>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '24px' }}>
              <MetricCard title="Процессор" value={dashboard.system.cpu} unit="%" bar={dashboard.system.cpu} />
              <MetricCard title="Память" value={dashboard.system.ram} unit="%" bar={dashboard.system.ram} />
              <MetricCard title="Диск" value={dashboard.system.disk} unit="%" bar={dashboard.system.disk} />
            </div>

            {/* Детали ресурсов */}
            <div style={{ fontSize: '0.875rem', color: '#94a3b8', marginBottom: '24px' }}>
              <div>Память: {dashboard.system.ram_used_gb} / {dashboard.system.ram_total_gb} ГБ</div>
              <div>Диск: {dashboard.system.disk_used_gb} / {dashboard.system.disk_total_gb} ГБ</div>
            </div>

            {/* Сводка по камерам и потокам */}
            <h3 style={{ margin: '16px 0 8px' }}>Сводка</h3>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '24px' }}>
              <MetricCard title="Всего камер" value={dashboard.stats.total_cameras} unit="" />
              <MetricCard title="Включено" value={dashboard.stats.enabled_cameras} unit="" />
              <MetricCard title="Отключено" value={dashboard.stats.disabled_cameras} unit="" />
              <MetricCard title="Потоков онлайн" value={dashboard.stats.online_streams} unit="" />
              <MetricCard title="Потоков офлайн" value={dashboard.stats.offline_streams} unit="" />
              <MetricCard title="Подключается" value={dashboard.stats.connecting_streams} unit="" />
            </div>

            {/* Таблица камер */}
            <h3 style={{ margin: '16px 0 8px' }}>Камеры</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #334155', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Имя</th>
                    <th style={{ padding: '8px' }}>Статус</th>
                    <th style={{ padding: '8px' }}>Включена</th>
                    <th style={{ padding: '8px' }}>Битрейт</th>
                    <th style={{ padding: '8px' }}>Сообщение</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.cameras.map((cam) => {
                    const badge = getStatusBadge(cam.state)
                    return (
                      <tr key={cam.id} style={{ borderBottom: '1px solid #1e293b' }}>
                        <td style={{ padding: '8px' }}>{cam.name}</td>
                        <td style={{ padding: '8px' }}>
                          <span className={`status-badge ${badge.cls}`}>{badge.text}</span>
                        </td>
                        <td style={{ padding: '8px' }}>{cam.enabled ? 'Да' : 'Нет'}</td>
                        <td style={{ padding: '8px' }}>{cam.metrics?.bitrate || '—'}</td>
                        <td style={{ padding: '8px', color: '#94a3b8' }}>{cam.msg || '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'dashboard' && !dashboard && (
          <div>Загрузка дашборда...</div>
        )}

        {/* ---------- КОНФИГУРАЦИЯ ---------- */}
        {activeTab === 'config' && (
          <div>
            <h2>Конфигурация</h2>
            <pre style={{ background: '#1e293b', padding: '12px', borderRadius: '6px', overflow: 'auto' }}>
              {JSON.stringify(config, null, 2)}
            </pre>
          </div>
        )}

        {/* ---------- КАМЕРЫ ---------- */}
        {activeTab === 'cameras' && (
          <div>
            <h2>Камеры</h2>
            <ul style={{ lineHeight: '1.8' }}>
              {cameras.map((cam) => (
                <li key={cam.id}>
                  {cam.name} — {cam.enabled ? '✅ включена' : '❌ отключена'}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* ---------- НАБОРЫ ---------- */}
        {activeTab === 'sets' && (
          <div>
            <h2>Наборы</h2>
            <pre style={{ background: '#1e293b', padding: '12px', borderRadius: '6px', overflow: 'auto' }}>
              {JSON.stringify(sets, null, 2)}
            </pre>
          </div>
        )}

        {/* ---------- ЛОГИ ---------- */}
        {activeTab === 'logs' && (
          <div>
            <h2>Логи потоков</h2>
            <pre style={{
              background: '#1e293b', padding: '12px', borderRadius: '6px',
              maxHeight: '400px', overflow: 'auto',
            }}>
              {Object.keys(logs).length === 0
                ? 'Логи пусты'
                : Object.entries(logs).map(([rid, lines]) =>
                    `\n--- ${rid} ---\n${lines.join('\n')}`
                  ).join('\n')}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/SettingsPage.jsx (визуальный дашборд)"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in app/routes/api.py frontend/src/pages/SettingsPage.jsx; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Дашборд реализован"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что теперь в дашборде:"
echo "  • Системные ресурсы: CPU, RAM, диск (прогресс-бары)"
echo "  • Сводка: всего камер, включено/отключено, потоки"
echo "  • Таблица камер с текущими статусами"
echo "  • Автообновление каждые 3 секунды"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 → Настройки → Дашборд"
