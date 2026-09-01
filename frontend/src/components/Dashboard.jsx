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
            {(!sets || sets.length === 0) && <div className="empty-state">Наборы не созданы</div>}
{(sets ?? []).map(set => (
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
