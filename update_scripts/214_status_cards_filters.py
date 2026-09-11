#!/usr/bin/env python3
"""
214. update_scripts/214_status_cards_filters.py
----------------------------------------------------------------------------
  • hls_worker.py: при переподключении статус «недоступна» НЕ сбрасывается
    (msg меняется на «Переподключение...», state остаётся)
  • CameraHealth.jsx:
      - плашки: цифра в одну строку с названием
      - клик по плашке = фильтр (мульти, AND); повторный клик — сброс
      - «Стримится» → «Подключено», «Ошибок» → «Недоступно»

ЗАПУСК: python update_scripts/214_status_cards_filters.py
"""

import sys
from pathlib import Path


def find_project_root():
    p = Path.cwd()
    while True:
        if (p / "frontend").is_dir() and (p / "update_scripts").is_dir():
            return p
        parent = p.parent
        if parent == p:
            print("[FAIL] Не найден корень проекта")
            sys.exit(1)
        p = parent


CAMERA_HEALTH_V2 = '''// ============================================================
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

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch('/api/health/cameras')
        if (r.ok && alive) setData(await r.json())
      } catch (e) {
        /* сервер перезапускается — ждём следующий тик */
      }
    }
    load()
    const t = setInterval(load, 5000)
    return () => { alive = false; clearInterval(t) }
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
'''


def patch_hls_worker(root):
    print("--- hls_worker.py: «недоступна» не сбрасывается при переподключении ---")
    f = root / "app" / "workers" / "hls_worker.py"
    b = f.with_suffix(".py.bak-214")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "PATCH-214" in c:
        print("  [OK] уже применён")
        return True

    old = '                    manager.set_status(route_id, "подключение", "Запуск потока...")'
    new = (
        '                    # PATCH-214: не сбрасываем «недоступна» при переподключении\n'
        '                    _prev_st = manager.get_status(route_id) or {}\n'
        '                    if _prev_st.get("state") == "недоступна":\n'
        '                        manager.set_status(route_id, "недоступна", "Переподключение...")\n'
        '                    else:\n'
        '                        manager.set_status(route_id, "подключение", "Запуск потока...")'
    )

    if old in c:
        c = c.replace(old, new, 1)
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] reconnect сохраняет «недоступна»")
            return True
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            return False
    print("  [FAIL] якорь не найден — откат")
    f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
    return False


def rewrite_camera_health(root):
    print("--- CameraHealth.jsx: плашки-фильтры + переименования ---")
    f = root / "frontend" / "src" / "components" / "CameraHealth.jsx"
    b = f.with_suffix(".jsx.bak-214")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    f.write_text(CAMERA_HEALTH_V2, encoding="utf-8")
    print(f"  [OK] переписан ({f.stat().st_size} bytes)")
    return True


def main():
    root = find_project_root()
    print("=" * 76)
    print("214: плашки-фильтры + стабильный статус «недоступна»")
    print("=" * 76)
    print()

    ok = True
    ok &= patch_hls_worker(root)
    ok &= rewrite_camera_health(root)

    if not ok:
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Перезапуск сервера + сборка:")
    print()
    print(f"  cd {root}/frontend && npm run build")
    print(f"  cd {root} && python main.py   (рестарт обязателен — правка backend)")
    print()
    print("Ожидаемо на /status (Ctrl+F5):")
    print("  • Плашки в одну строку: [📦 Всего 24] [✅ Включено 17] ...")
    print("  • Подписи: «Подключено» (вместо Стримится), «Недоступно» (вместо Ошибок)")
    print("  • Клик по «Недоступно» → таблица фильтруется; клик по «Включено» →")
    print("    пересечение: включённые И недоступные")
    print("  • Повторный клик / «✕ Сбросить фильтры» — сброс")
    print("  • Через ~10 сек после старта: «Недоступно 17», «Подключение 0»")
    print("    (переподключения больше не сбрасывают статус)")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat(status): clickable filter cards + stable unavailable state (PATCH-214)" \\')
    print('  -m "hls_worker: reconnect keeps state=недоступна (msg=Переподключение...)" \\')
    print('  -m "CameraHealth: cards single-line, click = multi-filter (AND)" \\')
    print('  -m "labels: Стримится→Подключено, Ошибок→Недоступно" \\')
    print('  -m "reset button + empty-state hint for filters"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()