#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 36: УЛУЧШЕННЫЙ ДАШБОРД
#  ------------------------------------------------------------
#  Что улучшает:
#    1. API endpoint /api/dashboard — детальная статистика:
#       • Общая статистика камер (всего/онлайн/оффлайн/ошибки)
#       • Нагрузка системы (CPU/RAM/диск/сеть)
#       • Статистика по наборам
#       • Список проблемных камер
#       • Последние события
#    2. Frontend компонент Dashboard.jsx — визуализация:
#       • Карточки с ключевыми метриками
#       • Прогресс-бары нагрузки
#       • Таблицы проблемных камер
#       • Статусы наборов
#    3. SettingsPage.jsx — новая вкладка "Дашборд"
#
#  Запуск:   bash 36_dashboard_improve.sh
#  После:    bash build_frontend.sh && python main.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# ЧАСТЬ 1: Улучшенный API endpoint для дашборда
# ============================================================
# Обновляем app/routes/api.py с детальной статистикой.
# Если файл уже существует, добавляем улучшенную версию.
# ============================================================

# Создаём отдельный модуль для дашборда, чтобы не трогать основной api.py
cat > "$PROJECT_DIR/app/routes/dashboard.py" << 'PYEOF_DASHBOARD'
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
PYEOF_DASHBOARD
echo "  ✔ app/routes/dashboard.py (улучшенный дашборд)"

# ============================================================
# ЧАСТЬ 2: Обновление регистрации роутов
# ============================================================
cat > "$PROJECT_DIR/app/routes/__init__.py" << 'PYEOF_ROUTES'
# -*- coding: utf-8 -*-
"""
app/routes/__init__.py
======================
Регистрация всех роутов приложения.

Модули:
  - api            : основные API endpoints
  - stream         : SSE stream статусов
  - hls            : раздача HLS сегментов
  - excel_import   : импорт камер из Excel
  - dashboard      : улучшенный дашборд (НОВОЕ в v36)
"""
from app.routes import api, stream, hls, excel_import, dashboard


def register_routes(app):
    """
    Регистрирует все роуты в Flask приложении.

    Args:
        app: Flask application instance
    """
    api.register(app)
    stream.register(app)
    hls.register(app)
    excel_import.register(app)
    dashboard.register(app)
PYEOF_ROUTES
echo "  ✔ app/routes/__init__.py (добавлен dashboard)"

# ============================================================
# ЧАСТЬ 3: Компонент дашборда для фронтенда
# ============================================================
cat > "$PROJECT_DIR/frontend/src/components/Dashboard.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — компонент дашборда
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v36):
//  • Карточки с ключевыми метриками
//  • Прогресс-бары нагрузки системы
//  • Таблицы проблемных камер
//  • Статусы наборов
// ============================================================
import { useState, useEffect } from 'react'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadDashboard()
    // Обновляем каждые 5 секунд
    const interval = setInterval(loadDashboard, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadDashboard = async () => {
    try {
      const response = await fetch('/api/dashboard')
      const result = await response.json()
      setData(result)
      setLoading(false)
      setError(null)
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
        Загрузка дашборда...
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: '#dc2626' }}>
        ❌ Ошибка загрузки: {error}
      </div>
    )
  }

  if (!data) {
    return null
  }

  const { cameras, system, sets, problem_cameras } = data

  // Вспомогательный компонент карточки метрики
  const MetricCard = ({ title, value, subtitle, color = '#2563eb' }) => (
    <div style={{
      background: '#1e293b',
      borderRadius: '8px',
      padding: '16px',
      border: '1px solid #334155',
      minWidth: '150px',
      flex: 1,
    }}>
      <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>
        {title}
      </div>
      <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color }}>
        {value}
      </div>
      {subtitle && (
        <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
          {subtitle}
        </div>
      )}
    </div>
  )

  // Вспомогательный компонент прогресс-бара
  const ProgressBar = ({ label, value, max, color = '#2563eb' }) => {
    const percent = max > 0 ? Math.round((value / max) * 100) : 0
    return (
      <div style={{ marginBottom: '12px' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: '4px',
          fontSize: '0.875rem',
        }}>
          <span>{label}</span>
          <span style={{ color: '#94a3b8' }}>
            {value} / {max} ({percent}%)
          </span>
        </div>
        <div style={{
          height: '8px',
          background: '#334155',
          borderRadius: '4px',
          overflow: 'hidden',
        }}>
          <div style={{
            height: '100%',
            width: `${percent}%`,
            background: color,
            borderRadius: '4px',
            transition: 'width 0.3s ease',
          }} />
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard-container">
      {/* Общая статистика камер */}
      <h3 style={{ marginBottom: '12px' }}>📹 Камеры</h3>
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '24px' }}>
        <MetricCard
          title="Всего"
          value={cameras.total}
          subtitle={`${cameras.enabled} включено, ${cameras.disabled} выключено`}
        />
        <MetricCard
          title="Онлайн"
          value={cameras.online}
          color="#059669"
          subtitle="Потоки активны"
        />
        <MetricCard
          title="Оффлайн"
          value={cameras.offline}
          color="#dc2626"
          subtitle="Нет соединения"
        />
        <MetricCard
          title="Подключение"
          value={cameras.connecting}
          color="#d97706"
          subtitle="В процессе"
        />
      </div>

      {/* Нагрузка системы */}
      <h3 style={{ marginBottom: '12px' }}>💻 Система</h3>
      <div style={{
        background: '#1e293b',
        borderRadius: '8px',
        padding: '16px',
        border: '1px solid #334155',
        marginBottom: '24px',
      }}>
        <ProgressBar
          label="CPU"
          value={system.cpu_percent}
          max={100}
          color={system.cpu_percent > 80 ? '#dc2626' : system.cpu_percent > 50 ? '#d97706' : '#059669'}
        />
        <ProgressBar
          label="Память"
          value={system.memory_used_mb}
          max={system.memory_total_mb}
          color={system.memory_percent > 80 ? '#dc2626' : system.memory_percent > 50 ? '#d97706' : '#059669'}
        />
        <ProgressBar
          label="Диск"
          value={system.disk_used_gb}
          max={system.disk_total_gb}
          color={system.disk_percent > 80 ? '#dc2626' : system.disk_percent > 50 ? '#d97706' : '#059669'}
        />

        <div style={{
          display: 'flex',
          gap: '16px',
          fontSize: '0.75rem',
          color: '#64748b',
          marginTop: '12px',
        }}>
          <span>ОС: {system.platform}</span>
          <span>Python: {system.python_version}</span>
          <span>Аптайм: {Math.round(system.uptime / 3600)}ч</span>
        </div>
      </div>

      {/* Статусы наборов */}
      <h3 style={{ marginBottom: '12px' }}>📦 Наборы</h3>
      <div style={{
        background: '#1e293b',
        borderRadius: '8px',
        padding: '16px',
        border: '1px solid #334155',
        marginBottom: '24px',
      }}>
        {sets.length === 0 ? (
          <div style={{ color: '#94a3b8' }}>Нет наборов</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
            {sets.map(set => (
              <div key={set.id} style={{
                padding: '12px',
                background: '#0b0d10',
                borderRadius: '6px',
                border: '1px solid #334155',
              }}>
                <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                  {set.name}
                </div>
                <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>
                  Камер: {set.total_cameras} (сетка {set.max_columns}×{set.max_rows})
                </div>
                <div style={{ fontSize: '0.875rem', marginTop: '4px' }}>
                  <span style={{ color: '#059669' }}>● {set.online}</span>
                  {' / '}
                  <span style={{ color: '#dc2626' }}>● {set.offline}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Проблемные камеры */}
      <h3 style={{ marginBottom: '12px' }}>⚠️ Проблемные камеры</h3>
      <div style={{
        background: '#1e293b',
        borderRadius: '8px',
        padding: '16px',
        border: '1px solid #334155',
      }}>
        {problem_cameras.length === 0 ? (
          <div style={{ color: '#059669' }}>✅ Все камеры в порядке</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <th style={{ textAlign: 'left', padding: '8px', color: '#94a3b8' }}>Камера</th>
                  <th style={{ textAlign: 'left', padding: '8px', color: '#94a3b8' }}>Расположение</th>
                  <th style={{ textAlign: 'left', padding: '8px', color: '#94a3b8' }}>Статус</th>
                  <th style={{ textAlign: 'left', padding: '8px', color: '#94a3b8' }}>Сообщение</th>
                </tr>
              </thead>
              <tbody>
                {problem_cameras.map(cam => (
                  <tr key={cam.id} style={{ borderBottom: '1px solid #334155' }}>
                    <td style={{ padding: '8px' }}>{cam.name}</td>
                    <td style={{ padding: '8px', color: '#94a3b8' }}>{cam.location || '—'}</td>
                    <td style={{ padding: '8px' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        background: cam.state === 'недоступна' ? '#7f1d1d' : '#7c2d12',
                        color: '#fff',
                      }}>
                        {cam.state}
                      </span>
                    </td>
                    <td style={{ padding: '8px', color: '#94a3b8', fontSize: '0.875rem' }}>
                      {cam.message || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/components/Dashboard.jsx (компонент дашборда)"

# ============================================================
# ЧАСТЬ 4: Обновление SettingsPage с вкладкой Дашборд
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/SettingsPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница настроек
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v36):
//  • Добавлена вкладка "Дашборд" с улучшенной статистикой
//  • Карточки метрик, прогресс-бары, таблицы
// ============================================================
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import Header from '../components/Header'
import Dashboard from '../components/Dashboard'
import Toasts from '../components/Toasts'
import { getSets, saveSets, getConfig } from '../api'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [setsData, setSetsData] = useState(null)
  const [configData, setConfigData] = useState(null)
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const sets = await getSets()
      setSetsData(sets)
      const config = await getConfig()
      setConfigData(config)
    } catch (e) {
      console.error('Ошибка загрузки данных:', e)
    }
  }

  const handleExcelImport = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    const validTypes = [
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ]
    if (!validTypes.includes(file.type) && !file.name.endsWith('.xls') && !file.name.endsWith('.xlsx')) {
      if (window.addToast) {
        window.addToast('❌ Неверный формат файла. Используйте .xlsx или .xls', 'error')
      }
      return
    }

    setImporting(true)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/cameras/import-excel', {
        method: 'POST',
        body: formData,
      })

      const result = await response.json()

      if (result.success) {
        if (window.addToast) {
          window.addToast(`✅ ${result.message}. Перезагрузите страницу (F5)`, 'success')
        }
        await loadData()
      } else {
        if (window.addToast) {
          window.addToast(`❌ ${result.message}`, 'error')
        }
      }
    } catch (e) {
      console.error('Ошибка импорта:', e)
      if (window.addToast) {
        window.addToast(`❌ Ошибка импорта: ${e.message}`, 'error')
      }
    } finally {
      setImporting(false)
      event.target.value = ''
    }
  }

  return (
    <div className="page">
      <Header />

      <h1 className="page-title">Настройки</h1>

      {/* Вкладки */}
      <div className="tabs">
        <button
          className={`btn ${activeTab === 'dashboard' ? 'btn-primary' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          📊 Дашборд
        </button>
        <button
          className={`btn ${activeTab === 'sets' ? 'btn-primary' : ''}`}
          onClick={() => setActiveTab('sets')}
        >
          📦 Наборы
        </button>
        <button
          className={`btn ${activeTab === 'config' ? 'btn-primary' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          ⚙️ Конфигурация
        </button>
        <Link to="/" className="btn">
          ← Назад к камерам
        </Link>
      </div>

      {/* Вкладка "Дашборд" */}
      {activeTab === 'dashboard' && (
        <div className="tab-content">
          <Dashboard />
        </div>
      )}

      {/* Вкладка "Наборы" */}
      {activeTab === 'sets' && (
        <div className="tab-content">
          <h2>Управление наборами камер</h2>

          <div style={{
            marginBottom: '20px',
            padding: '16px',
            background: '#1e293b',
            borderRadius: '8px',
            border: '1px solid #334155'
          }}>
            <h3 style={{ marginBottom: '12px' }}>📥 Импорт из Excel</h3>
            <p style={{ color: '#94a3b8', marginBottom: '12px' }}>
              Загрузите Excel файл с камерами. Файл должен содержать колонки:
              <br />
              <strong>ID</strong> (обязательно), <strong>main_url</strong> (обязательно),
              name, sub_url, enabled, comment, audio, location
            </p>

            <label className="btn btn-primary" style={{ cursor: 'pointer' }}>
              {importing ? '⏳ Загрузка...' : '📥 Выбрать Excel файл'}
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleExcelImport}
                disabled={importing}
                style={{ display: 'none' }}
              />
            </label>
          </div>

          {setsData ? (
            <div>
              <p>Активный набор: <strong>{setsData.default_set || 'не выбран'}</strong></p>
              <p>Всего наборов: <strong>{Object.keys(setsData.sets || {}).length}</strong></p>
            </div>
          ) : (
            <p>Загрузка...</p>
          )}
        </div>
      )}

      {/* Вкладка "Конфигурация" */}
      {activeTab === 'config' && (
        <div className="tab-content">
          <h2>Конфигурация системы</h2>
          {configData ? (
            <pre style={{
              background: '#0b0d10',
              padding: '16px',
              borderRadius: '8px',
              overflow: 'auto',
              fontSize: '0.875rem'
            }}>
              {JSON.stringify(configData, null, 2)}
            </pre>
          ) : (
            <p>Загрузка...</p>
          )}
        </div>
      )}

      <Toasts />
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/SettingsPage.jsx (вкладка Дашборд)"

# ============================================================
# ЧАСТЬ 5: Установка зависимостей (если нужно)
# ============================================================
echo ""
echo "📦 Проверка зависимостей..."
if ! python -c "import psutil" 2>/dev/null; then
  echo "⚠️  psutil не установлен. Для полной статистики системы установите:"
  echo "   pip install psutil"
else
  echo "✅ psutil установлен"
fi

# ============================================================
# Проверка всех файлов
# ============================================================
echo ""
echo "🔍 Проверка созданных файлов..."

for f in app/routes/dashboard.py app/routes/__init__.py frontend/src/components/Dashboard.jsx frontend/src/pages/SettingsPage.jsx; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Дашборд улучшен"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что добавлено:"
echo ""
echo "📊 Дашборд показывает:"
echo "  • Общая статистика камер (всего/онлайн/оффлайн/подключение)"
echo "  • Нагрузка системы (CPU/память/диск) с прогресс-барами"
echo "  • Статусы наборов (камер в наборе, онлайн/оффлайн)"
echo "  • Список проблемных камер (включены, но не в сети)"
echo ""
echo "🚀 Использование:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000/settings"
echo "     Перейдите на вкладку '📊 Дашборд'"
echo ""
echo "📦 Опционально: pip install psutil (для полной статистики)"