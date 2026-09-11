#!/usr/bin/env python3
"""
221. update_scripts/221_health_sort.py
----------------------------------------------------------------------------
CameraHealth.jsx: добавляет сортировку по ID / Имени / IP в таблицу
состояния камер на /status.

  • useState: sortCol ('id'|'name'|'ip'), sortDir (1|-1)
  • Кликабельные <th> с индикаторами ▲/▼
  • Сортировка работает вместе с фильтрами-плашками (AND)
  • numeric-aware localeCompare для IP

ЗАПУСК: python update_scripts/221_health_sort.py
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


def main():
    root = find_project_root()
    f = root / "frontend" / "src" / "components" / "CameraHealth.jsx"

    print("=" * 76)
    print("221: сортировка ID/Имя/IP в «Состоянии камер»")
    print("=" * 76)
    print()

    b = f.with_suffix(".jsx.bak-221")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    # 1. Добавить state для сортировки
    old_state = "  const [active, setActive] = useState([])  // PATCH-214: активные фильтры (AND)"
    new_state = (
        "  const [active, setActive] = useState([])  // PATCH-214: активные фильтры (AND)\n"
        "  const [sortCol, setSortCol] = useState('id')     // PATCH-221\n"
        "  const [sortDir, setSortDir] = useState(1)"
    )
    if "const [sortCol, setSortCol]" not in c:
        if old_state in c:
            c = c.replace(old_state, new_state, 1)
            n += 1
            print("  [OK] state sortCol/sortDir добавлен")
        else:
            print("  [FAIL] state-якорь не найден — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

    # 2. Заменить rows sort на многоколоночный
    old_sort = """  const rows = Object.entries(data.cameras)
    .filter(([, cam]) => active.every(k => FILTERS[k]?.test(cam)))
    .sort(([a], [b]) => a.localeCompare(b))"""
    new_sort = """  // PATCH-221: сортировка по выбранной колонке
  const rows = Object.entries(data.cameras)
    .filter(([, cam]) => active.every(k => FILTERS[k]?.test(cam)))
    .sort(([aId, aCam], [bId, bCam]) => {
      const av = sortCol === 'id' ? aId : (sortCol === 'name' ? aCam.name : aCam.ip)
      const bv = sortCol === 'id' ? bId : (sortCol === 'name' ? bCam.name : bCam.ip)
      return String(av ?? '').localeCompare(String(bv ?? ''), undefined, { numeric: true }) * sortDir
    })"""
    if old_sort in c:
        c = c.replace(old_sort, new_sort, 1)
        n += 1
        print("  [OK] rows: сортировка по sortCol + numeric-aware")

    # 3. Заменить <th> на кликабельные (ID, Имя, IP)
    old_th_id = "<th style={th}>ID</th>"
    new_th_id = """<th
              onClick={() => { setSortCol('id'); setSortDir(d => sortCol === 'id' ? -d : 1) }}
              style={{ ...th, cursor: 'pointer', userSelect: 'none', color: sortCol === 'id' ? '#38bdf8' : '#94a3b8' }}
            >
              ID {sortCol === 'id' && (sortDir === 1 ? '▲' : '▼')}
            </th>"""
    old_th_name = "<th style={th}>Имя</th>"
    new_th_name = """<th
              onClick={() => { setSortCol('name'); setSortDir(d => sortCol === 'name' ? -d : 1) }}
              style={{ ...th, cursor: 'pointer', userSelect: 'none', color: sortCol === 'name' ? '#38bdf8' : '#94a3b8' }}
            >
              Имя {sortCol === 'name' && (sortDir === 1 ? '▲' : '▼')}
            </th>"""
    old_th_ip = "<th style={th}>IP</th>"
    new_th_ip = """<th
              onClick={() => { setSortCol('ip'); setSortDir(d => sortCol === 'ip' ? -d : 1) }}
              style={{ ...th, cursor: 'pointer', userSelect: 'none', color: sortCol === 'ip' ? '#38bdf8' : '#94a3b8' }}
            >
              IP {sortCol === 'ip' && (sortDir === 1 ? '▲' : '▼')}
            </th>"""

    for old, new, label in [
        (old_th_id, new_th_id, "ID"),
        (old_th_name, new_th_name, "Имя"),
        (old_th_ip, new_th_ip, "IP"),
    ]:
        if old in c:
            c = c.replace(old, new, 1)
            n += 1
            print(f"  [OK] <th>{label}</th> → кликабельный")
        else:
            print(f"  [SKIP] <th>{label}</th> не найден")

    if n < 4:
        print(f"  [WARN] применено только {n}/5 — проверьте файл вручную")

    f.write_text(c, encoding="utf-8")
    print(f"  [OK] файл сохранён (изменений: {n})")

    print()
    print("=" * 76)
    print("✅ PATCH-221 готов! Сборка:")
    print()
    print(f"  cd {root}/frontend && npm run build")
    print()
    print("Откройте /status (Ctrl+F5):")
    print("  • Клик по ID ▲ → сортировка по ID (повторный клик — ▼ desc)")
    print("  • Клик по Имя — сортировка по имени камеры")
    print("  • Клик по IP — numeric-aware (172.16.103.9 < 172.16.103.100)")
    print("  • Работает вместе с фильтрами-плашками: клик 🔴 + клик ▲ по IP")
    print("    = только недоступные, отсортированные по IP")
    print("  • Активная колонка подсвечивается голубым (#38bdf8)")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat(status): sortable ID/Name/IP columns in camera table (PATCH-221)" \\')
    print('  -m "CameraHealth: clickable <th> with ▲/▼ indicators" \\')
    print('  -m "numeric-aware localeCompare for IP addresses" \\')
    print('  -m "active column highlighted in cyan; works with AND-filters"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()