#!/usr/bin/env python3
"""
218.2 update_scripts/218_2_sse_frontend.py
----------------------------------------------------------------------------
CameraHealth.jsx: EventSource вместо setInterval+fetch.
  • SSE primary: обновления пушатся сервером мгновенно
  • Polling fallback: если SSE упал/недоступен — каждые 5 сек
  • Индикатор режима в заголовке: ⚡ live / 🔄 poll

ЗАПУСК: python update_scripts/218_2_sse_frontend.py
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


OLD_EFFECT = """  useEffect(() => {
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
  }, [])"""

NEW_EFFECT = """  // PATCH-218.2: SSE primary + polling fallback
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
  }, [])"""

OLD_HEADER = """        <span style={{ fontSize: '11px', color: '#64748b' }}>
          обновлено {new Date(data.ts * 1000).toLocaleTimeString()}
        </span>"""

NEW_HEADER = """        <span style={{ fontSize: '11px', color: '#64748b' }}>
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
        </span>"""


def main():
    root = find_project_root()
    f = root / "frontend" / "src" / "components" / "CameraHealth.jsx"

    print("=" * 76)
    print("218.2: CameraHealth на EventSource (SSE + fallback)")
    print("=" * 76)
    print()

    b = f.with_suffix(".jsx.bak-2182")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    if "EventSource" in c:
        print("  [OK] EventSource уже подключён")
    else:
        if OLD_EFFECT in c:
            c = c.replace(OLD_EFFECT, NEW_EFFECT, 1)
            n += 1
            print("  [OK] useEffect: EventSource + polling fallback")
        else:
            print("  [FAIL] якорь useEffect не найден — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        if OLD_HEADER in c:
            c = c.replace(OLD_HEADER, NEW_HEADER, 1)
            n += 1
            print("  [OK] индикатор режима ⚡ live / 🔄 poll")
        else:
            print("  [WARN] якорь заголовка не найден (индикатор пропущен)")

        f.write_text(c, encoding="utf-8")

    print()
    print("=" * 76)
    print("✅ Готово! Сборка + проверка:")
    print()
    print(f"  cd {root}/frontend && npm run build")
    print(f"  cd {root} && python main.py")
    print()
    print("Откройте /status (Ctrl+F5):")
    print("  • Бейдж ⚡ live рядом с таймстампом = SSE работает")
    print("  • Обновления приходят МГНОВЕННО при смене статуса воркера")
    print("  • Если SSE упадёт — бейдж 🔄 poll + опрос каждые 5 сек")
    print()
    print("Проверка мгновенности: включите/выключите камеру на /cameras —")
    print("строка в таблице /status обновится без задержки в 5 сек.")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat(sse): CameraHealth on EventSource with polling fallback (PATCH-218.2)" \\')
    print('  -m "SSE primary: instant pushes from /api/health/cameras/stream" \\')
    print('  -m "fallback: 5s polling if EventSource errors" \\')
    print('  -m "mode badge: ⚡ live / 🔄 poll next to timestamp"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()