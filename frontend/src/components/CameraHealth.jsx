// ============================================================
//  GRYPHONE — Camera Health section (PATCH-210)
//  ------------------------------------------------------------
//  Секция здоровья камер для страницы /status.
//  Самодостаточна: fetch /api/health/cameras + автообновление 5 сек.
// ============================================================
import { useState, useEffect } from 'react'

const STATE_STYLE = {
  'в_сети':      { bg: '#065f46', fg: '#d1fae5', icon: '🟢', label: 'Стримит' },
  'подключение': { bg: '#854d0e', fg: '#fef3c7', icon: '🟡', label: 'Подключение' },
  'недоступна':  { bg: '#991b1b', fg: '#fecaca', icon: '🔴', label: 'Ошибка' },
  'отключена':   { bg: '#374151', fg: '#d1d5db', icon: '⚪', label: 'Выключена' },
  'не_запущен':  { bg: '#9a3412', fg: '#fed7aa', icon: '🟠', label: 'Не запущен' },
}

function StateCell({ st }) {
  const c = STATE_STYLE[st?.state] || STATE_STYLE['не_запущен']
  const fps = st?.metrics?.fps ? ` • ${st.metrics.fps} fps` : ''
  return (
    <span
      title={`${c.label}: ${st?.msg || ''}${fps}`}
      style={{
        background: c.bg, color: c.fg,
        padding: '4px 10px', borderRadius: '6px',
        fontSize: '11px', fontWeight: 600,
        display: 'inline-block', minWidth: '96px', textAlign: 'center',
        whiteSpace: 'nowrap',
      }}
    >
      {c.icon} {c.label}{fps && <span style={{ opacity: 0.75, marginLeft: 4 }}>{fps}</span>}
    </span>
  )
}

export default function CameraHealth() {
  const [data, setData] = useState(null)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch('/api/health/cameras')
        if (r.ok && alive) setData(await r.json())
      } catch (e) {
        /* сервер перезапускается — молча ждём следующий тик */
      }
    }
    load()
    const t = setInterval(load, 5000)
    return () => { alive = false; clearInterval(t) }
  }, [])

  if (!data) {
    return (
      <div style={{ textAlign: 'center', padding: '30px', color: '#64748b' }}>
        ⏳ Загрузка здоровья камер...
      </div>
    )
  }

  const s = data.summary || {}
  const cards = [
    { label: 'Всего', value: s.total ?? 0, icon: '📦', color: '#f1f5f9' },
    { label: 'Включено', value: s.enabled ?? 0, icon: '✅', color: '#22c55e' },
    { label: 'Выключено', value: s.disabled ?? 0, icon: '⚪', color: '#94a3b8' },
    { label: 'Стримится', value: s.streaming ?? 0, icon: '🟢', color: '#22c55e' },
    { label: 'Подключение', value: s.connecting ?? 0, icon: '🟡', color: '#eab308' },
    { label: 'Ошибок', value: s.errors ?? 0, icon: '🔴', color: '#ef4444' },
  ]

  const filters = [
    ['all', 'Все', s.total],
    ['enabled', 'Включённые', s.enabled],
    ['disabled', 'Выключенные', s.disabled],
    ['streaming', 'Стримящиеся', s.streaming],
    ['error', 'С ошибкой', s.errors],
  ]

  const match = (cam) => {
    if (filter === 'all') return true
    if (filter === 'enabled') return cam.enabled
    if (filter === 'disabled') return !cam.enabled
    if (filter === 'streaming')
      return cam.main?.state === 'в_сети' || cam.sub?.state === 'в_сети'
    if (filter === 'error')
      return cam.main?.state === 'недоступна' || cam.sub?.state === 'недоступна'
    return true
  }

  const rows = Object.entries(data.cameras)
    .filter(([, cam]) => match(cam))
    .sort(([a], [b]) => a.localeCompare(b))

  const th = {
    padding: '10px 12px', background: '#1e293b', color: '#94a3b8',
    textAlign: 'left', fontWeight: 600, fontSize: '12px',
    borderBottom: '1px solid #334155',
  }
  const td = { padding: '8px 12px', fontSize: '12px' }

  return (
    <div style={{ marginTop: '28px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginBottom: '14px' }}>
        <h2 style={{ margin: 0, fontSize: '18px', color: '#f1f5f9' }}>🏥 Здоровье камер</h2>
        <span style={{ fontSize: '11px', color: '#64748b' }}>
          обновлено {new Date(data.ts * 1000).toLocaleTimeString()}
        </span>
      </div>

      {/* Summary */}
      <div style={{
        display: 'grid', gap: '10px', marginBottom: '14px',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
      }}>
        {cards.map(c => (
          <div key={c.label} style={{
            background: '#1e293b', border: '1px solid #334155',
            borderRadius: '10px', padding: '12px 16px',
          }}>
            <div style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 500 }}>
              {c.icon} {c.label}
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: c.color }}>
              {c.value}
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '6px', marginBottom: '12px', flexWrap: 'wrap' }}>
        {filters.map(([k, label, cnt]) => (
          <button
            key={k}
            onClick={() => setFilter(k)}
            style={{
              padding: '5px 12px', borderRadius: '6px', fontSize: '12px',
              border: filter === k ? '1px solid #38bdf8' : '1px solid #334155',
              background: filter === k ? '#1e3a8a' : '#1e293b',
              color: '#f1f5f9', cursor: 'pointer',
            }}
          >
            {label} <span style={{ opacity: 0.6 }}>({cnt ?? 0})</span>
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{
          width: '100%', borderCollapse: 'collapse',
          background: '#0f172a', borderRadius: '10px', overflow: 'hidden',
        }}>
          <thead>
            <tr>
              <th style={th}>ID</th>
              <th style={th}>Имя</th>
              <th style={th}>IP</th>
              <th style={th}>Main</th>
              <th style={th}>Sub</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([id, cam]) => (
              <tr key={id} style={{ borderTop: '1px solid #1e293b' }}>
                <td style={{ ...td, color: '#f1f5f9', fontFamily: 'monospace' }}>{id}</td>
                <td style={{ ...td, color: '#cbd5e1' }}>{cam.name}</td>
                <td style={{ ...td, color: '#94a3b8', fontFamily: 'monospace' }}>{cam.ip}</td>
                <td style={td}><StateCell st={cam.main} /></td>
                <td style={td}><StateCell st={cam.sub} /></td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan="5" style={{ ...td, padding: '30px', textAlign: 'center', color: '#64748b' }}>
                  Нет камер, соответствующих фильтру
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
