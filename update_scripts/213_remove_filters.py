#!/usr/bin/env python3
"""
213. update_scripts/213_remove_filters.py
----------------------------------------------------------------------------
CameraHealth.jsx: полностью удаляет блок фильтров
(Все / Включённые / Выключенные / Стримящиеся / С ошибкой)
вместе со state, массивом filters и функцией match.
Таблица всегда показывает все камеры.

ЗАПУСК: python update_scripts/213_remove_filters.py
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


REPLACEMENTS = [
    # 1. state
    (
        "  const [data, setData] = useState(null)\n  const [filter, setFilter] = useState('all')\n",
        "  const [data, setData] = useState(null)\n",
        "state filter",
    ),
    # 2. массив filters + match + rows
    (
        """  const filters = [
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
    .sort(([a], [b]) => a.localeCompare(b))""",
        """  const rows = Object.entries(data.cameras)
    .sort(([a], [b]) => a.localeCompare(b))""",
        "filters/match/rows",
    ),
    # 3. JSX-блок фильтров
    (
        """      {/* Filters */}
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

""",
        "",
        "JSX фильтров",
    ),
    # 4. текст пустой таблицы
    (
        "Нет камер, соответствующих фильтру",
        "Нет данных о камерах",
        "текст пустой таблицы",
    ),
]


def main():
    root = find_project_root()
    f = root / "frontend" / "src" / "components" / "CameraHealth.jsx"

    print("=" * 76)
    print("213: удаление фильтров из «Состояния камер»")
    print("=" * 76)
    print()

    b = f.with_suffix(".jsx.bak-213")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    for old, new, label in REPLACEMENTS:
        if old in c:
            c = c.replace(old, new, 1)
            n += 1
            print(f"  [OK] {label}")
        else:
            print(f"  [SKIP] {label} — не найдено (уже удалено?)")

    if n == 0:
        print("  [FAIL] ничего не найдено — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # sanity: не осталось ссылок на filter
    leftovers = [w for w in ("setFilter", "filters.map", "match(cam)") if w in c]
    if leftovers:
        print(f"  [FAIL] остались ссылки: {leftovers} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    f.write_text(c, encoding="utf-8")
    print(f"  [OK] замен: {n}, файл сохранён")

    print()
    print("=" * 76)
    print("✅ Готово! Соберите и проверьте:")
    print()
    print(f"  cd {root}/frontend && npm run build")
    print("  Ctrl+F5 на http://127.0.0.1:5000/status")
    print()
    print("Ожидаемо: плашки summary + сразу таблица (без строки фильтров)")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "ui(status): remove filter buttons from camera state (PATCH-213)" \\')
    print('  -m "CameraHealth.jsx: table always shows all cameras" \\')
    print('  -m "removed filter state, match() and buttons row"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()