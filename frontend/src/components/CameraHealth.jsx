// ============================================================
//  GRYPHONE — Состояние камер (PATCH-210/214)
//  ------------------------------------------------------------
//  Секция состояния камер для страницы /status.
//  PATCH-214: плашки в одну строку; клик = мультифильтр (AND).
// ============================================================
import { useState, useEffect } from 'react'

const STATE_STYLE = {
  'в_сети':      { bg: '#065f46', fg: '#d1fae5', icon: '🟢', label: 'Подключено' },
  'подключение': { bg: '#854d0e', fg: '#fef3c7', icon: '🟡', label: 'Подключение' },
  'недоступна':  { bg: '#991b1b', fg: '#fecaca', icon: '🔴', label: 'Недоступна' },
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

// PATCH-214: предикаты фильтров (клик по плашке)
const FILTERS = {
  enabled:     { test: (c) => c.enabled },
  disabled:    { test: (c) => !c.enabled },
  connected:   { test: (c) => c.main?.state === 'в_сети' || c.sub?.state === 'в_сети' },
  connecting:  { test: (c) => c.main?.state === 'подключение' || c.sub?.state === 'подключение' },
  unavailable: { test: (c) => c.main?.state === 'недоступна' || c.sub?.state === 'недоступна' },
}

export default function CameraHealth() {
  const [data, setData] = useState(null)
  const [active, setActive] = useState([])  // PATCH-214: активные фильтры (AND)

  // PATCH-218.2: SSE primary + polling fallback
  const [mode, setMode] = useState('poll')

  useEffect(() => {
    let alive = true
    let es = null
    let pollTimer = null

    const applyData = (d) => { if (alive) setData(d) }

    const stopPolling = () => {
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
    }

    const startPolling = () => {
      if (pollTimer || !alive) return
      const load = async () => {
        try {
          const r = await fetch('/api/health/cameras')
          if (r.ok && alive) applyData(await r.json())
        } catch (e) { /* сервер перезапускается */ }
      }
      load()
      pollTimer = setInterval(load, 5000)
      if (alive) setMode('poll')
    }

    const startSSE = () => {
      try {
        es = new EventSource('/api/health/cameras/stream')
        es.onmessage = (e) => {
          try {
            applyData(JSON.parse(e.data))
            stopPolling()          // SSE работает — polling не нужен
            if (alive) setMode('live')
          } catch (err) { /* битый JSON — игнор */ }
        }
        es.onerror = () => {       // SSE упал — fallback на polling
          if (es) { es.close(); es = null }
          startPolling()
        }
      } catch (e) {
        startPolling()
      }
    }

    startSSE()

    return () => {
      alive = false
      if (es) es.close()
      stopPolling()
    }
  }, [])

  const toggleFilter = (key) => {
    if (!key) return
    setActive(a => (a.includes(key) ? a.filter(k => k !== key) : [...a, key]))
  }

  if (!data) {
    return (
      <div style={{ textAlign: 'center', padding: '30px', color: '#64748b' }}>
        ⏳ Загрузка состояния камер...
      </div>
    )
  }

  const s = data.summary || {}
  const cards = [
    { key: null,          label: 'Всего',       value: s.total ?? 0,      icon: '📦', color: '#f1f5f9' },
    { key: 'enabled',     label: 'Включено',    value: s.enabled ?? 0,    icon: '✅', color: '#22c55e' },
    { key: 'disabled',    label: 'Выключено',   value: s.disabled ?? 0,   icon: '⚪', color: '#94a3b8' },
    { key: 'connected',   label: 'Подключено',  value: s.streaming ?? 0,  icon: '🟢', color: '#22c55e' },
    { key: 'connecting',  label: 'Подключение', value: s.connecting ?? 0, icon: '🟡', color: '#eab308' },
    { key: 'unavailable', label: 'Недоступно',  value: s.errors ?? 0,     icon: '🔴', color: '#ef4444' },
  ]

  // PATCH-214: мультифильтр — пересечение (AND) всех активных предикатов
  const rows = Object.entries(data.cameras)
    .filter(([, cam]) => active.every(k => FILTERS[k]?.test(cam)))
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
        <h2 style={{ margin: 0, fontSize: '18px', color: '#f1f5f9' }}>📊 Состояние камер</h2>
        <span style={{ fontSize: '11px', color: '#64748b' }}>
          обновлено {new Date(data.ts * 1000).toLocaleTimeString()}
        </span>
        <span
          title={mode === 'live' ? 'SSE: сервер пушит обновления мгновенно' : 'Polling: опрос каждые 5 сек'}
          style={{
            fontSize: '10px', fontWeight: 600, padding: '2px 8px',
            borderRadius: '4px',
            background: mode === 'live' ? '#065f46' : '#854d0e',
            color: mode === 'live' ? '#d1fae5' : '#fef3c7',
          }}
        >
          {mode === 'live' ? '⚡ live' : '🔄 poll'}
        </span>
        {active.length > 0 && (
          <button
            onClick={() => setActive([])}
            style={{
              marginLeft: 'auto', padding: '4px 10px', fontSize: '11px',
              background: '#1e293b', color: '#94a3b8',
              border: '1px solid #334155', borderRadius: '6px', cursor: 'pointer',
            }}
          >
            ✕ Сбросить фильтры ({active.length})
          </button>
        )}
      </div>

      {/* PATCH-214: плашки в одну строку, клик = фильтр */}
      <div style={{
        display: 'grid', gap: '10px', marginBottom: '14px',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
      }}>
        {cards.map(c => {
          const isActive = c.key && active.includes(c.key)
          return (
            <div
              key={c.label}
              onClick={() => toggleFilter(c.key)}
              title={c.key ? 'Клик — фильтр по этому параметру' : undefined}
              style={{
                background: '#1e293b',
                border: isActive ? `1px solid ${c.color}` : '1px solid #334155',
                boxShadow: isActive ? `0 0 8px ${c.color}55` : 'none',
                borderRadius: '10px', padding: '10px 16px',
                display: 'flex', alignItems: 'center', gap: '8px',
                cursor: c.key ? 'pointer' : 'default',
                userSelect: 'none',
              }}
            >
              <span style={{ fontSize: '12px', color: '#94a3b8', fontWeight: 500, whiteSpace: 'nowrap' }}>
                {c.icon} {c.label}
              </span>
              <span style={{ fontSize: '20px', fontWeight: 700, color: c.color }}>
                {c.value}
              </span>
            </div>
          )
        })}
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
                  {active.length > 0
                    ? 'Нет камер под выбранные фильтры (клик по плашке — сброс)'
                    : 'Нет данных о камерах'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
