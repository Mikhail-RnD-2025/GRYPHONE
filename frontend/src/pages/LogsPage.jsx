// ============================================================
// GRYPHONE — страница логов
// ------------------------------------------------------------
// Отображает системные логи приложения в реальном времени.
// ============================================================

import { useState, useEffect, useRef } from 'react'
import Header from '../components/Header'

export default function LogsPage() {
  const [logs, setLogs] = useState([])
  const [filter, setFilter] = useState('all')
  const logsEndRef = useRef(null)

  // Загрузка логов с сервера
  useEffect(() => {
    loadLogs()
    const interval = setInterval(loadLogs, 5000) // Обновление каждые 5 сек
    return () => clearInterval(interval)
  }, [])

  const loadLogs = async () => {
    try {
      const response = await fetch('/api/logs')
      if (response.ok) {
        const data = await response.json()
        setLogs(data.logs || [])
      } else {
        // Если API недоступен, показываем заглушку
        setLogs([
          { timestamp: new Date().toISOString(), level: 'INFO', message: 'Система логов будет доступна после настройки сервера' },
          { timestamp: new Date().toISOString(), level: 'DEBUG', message: 'Заглушка логов для демонстрации интерфейса' },
        ])
      }
    } catch (e) {
      console.error('Ошибка загрузки логов:', e)
    }
  }

  // Автоскролл к последним логам
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const getLevelColor = (level) => {
    switch (level) {
      case 'ERROR': return '#dc2626'
      case 'WARNING': return '#d97706'
      case 'INFO': return '#059669'
      case 'DEBUG': return '#94a3b8'
      default: return '#e0e3e8'
    }
  }

  const filteredLogs = filter === 'all' 
    ? logs 
    : logs.filter(log => log.level.toLowerCase() === filter)

  return (
    <div className="page">
      <Header />
      <div className="section-header">
        <div className="section-header-left">
          <span className="section-icon">📜</span>
          <h1 className="section-title">Логи системы</h1>
        </div>
      </div>

      {/* Фильтр по уровню */}
      <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {['all', 'error', 'warning', 'info', 'debug'].map(level => (
          <button
            key={level}
            className={`btn ${filter === level ? 'btn-primary' : ''}`}
            onClick={() => setFilter(level)}
            style={{ padding: '6px 12px', fontSize: '0.8125rem' }}
          >
            {level === 'all' ? 'Все' : level.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Контейнер логов */}
      <div style={{
        background: '#0b0d10',
        border: '1px solid #1e293b',
        borderRadius: '8px',
        padding: '16px',
        overflowY: 'auto',
        flex: 1,
        minHeight: 0,
        fontFamily: 'Courier New, monospace',
        fontSize: '0.8125rem',
        lineHeight: 1.6,
      }}>
        {filteredLogs.length === 0 ? (
          <div style={{ color: '#64748b', textAlign: 'center', padding: '40px' }}>
            Нет логов для отображения
          </div>
        ) : (
          filteredLogs.map((log, index) => (
            <div key={index} style={{
              padding: '4px 0',
              borderBottom: '1px solid rgba(30, 41, 59, 0.5)',
              display: 'flex',
              gap: '12px',
            }}>
              <span style={{ color: '#64748b', flexShrink: 0 }}>
                {new Date(log.timestamp).toLocaleTimeString('ru-RU')}
              </span>
              <span style={{ 
                color: getLevelColor(log.level), 
                fontWeight: 600, 
                minWidth: '70px',
                flexShrink: 0,
              }}>
                [{log.level}]
              </span>
              <span style={{ color: '#e0e3e8' }}>{log.message}</span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  )
}
