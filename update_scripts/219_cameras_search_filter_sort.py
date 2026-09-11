#!/usr/bin/env python3
"""
219. update_scripts/219_cameras_search_filter_sort.py
----------------------------------------------------------------------------
CamerasEditor.jsx: поиск + фильтрация + сортировка по ID/Имени/IP

  • useState: search, enabledFilter, sortCol, sortDir
  • useMemo: visibleCameras (search ∩ filter → sort)
  • Панель: input поиска + select фильтра + счётчик + кнопка сброса
  • Кликабельные заголовки ID/Имя/IP со стрелками ▲/▼
  • Замена cameras.map → visibleCameras.map

ЗАПУСК: python update_scripts/219_cameras_search_filter_sort.py
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
    f = root / "frontend" / "src" / "components" / "CamerasEditor.jsx"

    print("=" * 76)
    print("219: поиск + фильтрация + сортировка в CamerasEditor")
    print("=" * 76)
    print()

    b = f.with_suffix(".jsx.bak-219")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    lines = f.read_text(encoding="utf-8").split("\n")
    n = 0

    # 1. Вставляем useState после последнего useState([...]) или useState({...})
    # Ищем последнюю строку с useState
    last_state_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if "useState" in lines[i] and ("[" in lines[i] or "{" in lines[i]):
            last_state_idx = i
            break

    if last_state_idx is None:
        print("  [FAIL] useState не найден")
        sys.exit(1)

    state_insert = """  const [search, setSearch] = useState('')  // PATCH-219
  const [enabledFilter, setEnabledFilter] = useState('all')
  const [sortCol, setSortCol] = useState('id')
  const [sortDir, setSortDir] = useState(1)"""

    if "const [search, setSearch]" not in "\n".join(lines):
        lines.insert(last_state_idx + 1, state_insert)
        n += 1
        print(f"  [OK] useState добавлен после строки {last_state_idx + 1}")
    else:
        print("  [SKIP] useState уже есть")

    # 2. Вставляем useMemo перед функцией loadCameras или handleEdit
    memo_anchor_idx = None
    for i, ln in enumerate(lines):
        if "const loadCameras = async" in ln or "const handleEdit = " in ln:
            memo_anchor_idx = i
            break

    if memo_anchor_idx is None:
        print("  [FAIL] якорь для useMemo не найден")
        sys.exit(1)

    memo_insert = """
  // PATCH-219: производный список камер (search ∩ filter → sort)
  const visibleCameras = useMemo(() => {
    let list = cameras
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      list = list.filter(c =>
        (c.id || '').toLowerCase().includes(q) ||
        (c.name || '').toLowerCase().includes(q) ||
        (c.ipaddress || '').toLowerCase().includes(q))
    }
    if (enabledFilter !== 'all')
      list = list.filter(c => enabledFilter === 'on' ? c.enabled : !c.enabled)
    return [...list].sort((a, b) => {
      const av = String(a[sortCol] ?? '').toLowerCase()
      const bv = String(b[sortCol] ?? '').toLowerCase()
      return av.localeCompare(bv, undefined, { numeric: true }) * sortDir
    })
  }, [cameras, search, enabledFilter, sortCol, sortDir])
"""

    if "const visibleCameras = useMemo" not in "\n".join(lines):
        lines.insert(memo_anchor_idx, memo_insert)
        n += 1
        print(f"  [OK] useMemo visibleCameras добавлен перед строкой {memo_anchor_idx}")
    else:
        print("  [SKIP] useMemo уже есть")

    # 3. Вставляем панель управления перед таблицей
    # Ищем строку с {/* Таблица камер */} или <div style={{ overflowX: 'auto'
    panel_anchor_idx = None
    for i, ln in enumerate(lines):
        if "{/* Таблица камер */}" in ln or (i > 0 and "overflowX: 'auto'" in lines[i] and "border:" in lines[i+1]):
            panel_anchor_idx = i
            break

    if panel_anchor_idx is None:
        print("  [FAIL] якорь для панели не найден")
        sys.exit(1)

    panel_insert = """      {/* PATCH-219: Панель поиска/фильтрации */}
      <div style={{
        display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap',
        padding: '12px', marginBottom: '12px',
        background: '#1e293b', border: '1px solid #334155', borderRadius: '8px',
      }}>
        <input
          type="text"
          placeholder="🔍 Поиск: ID, имя, IP..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            flex: '1 1 200px', padding: '8px 12px',
            background: '#0f172a', border: '1px solid #334155', borderRadius: '6px',
            color: '#e0e3e8', fontSize: '0.875rem', outline: 'none',
          }}
        />
        <select
          value={enabledFilter}
          onChange={(e) => setEnabledFilter(e.target.value)}
          style={{
            padding: '8px 12px', background: '#0f172a', border: '1px solid #334155',
            borderRadius: '6px', color: '#e0e3e8', fontSize: '0.875rem', cursor: 'pointer',
          }}
        >
          <option value="all">Все</option>
          <option value="on">Включённые</option>
          <option value="off">Выключенные</option>
        </select>
        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
          Найдено: <strong style={{ color: '#e0e3e8' }}>{visibleCameras.length}</strong> из {cameras.length}
        </span>
        {(search || enabledFilter !== 'all') && (
          <button
            onClick={() => { setSearch(''); setEnabledFilter('all') }}
            style={{
              padding: '6px 12px', background: '#dc2626', border: 'none',
              borderRadius: '6px', color: '#fff', fontSize: '0.75rem', cursor: 'pointer',
            }}
          >
            ✕ Сбросить
          </button>
        )}
      </div>

"""

    if "{/* PATCH-219: Панель" not in "\n".join(lines):
        lines.insert(panel_anchor_idx, panel_insert)
        n += 1
        print(f"  [OK] панель поиска/фильтрации вставлена перед строкой {panel_anchor_idx}")
    else:
        print("  [SKIP] панель уже есть")

    # 4. Заменяем статические <th> на кликабельные (ID/Имя/IP)
    # Ищем строки с <th>ID</th>, <th>Имя</th>, <th>IP:Порт</th>
    for i in range(len(lines)):
        if "<th style={{ padding: '12px', textAlign: 'left' }}>ID</th>" in lines[i]:
            lines[i] = """              <th
                onClick={() => { setSortCol('id'); setSortDir(d => sortCol === 'id' ? -d : 1) }}
                style={{ padding: '12px', textAlign: 'left', cursor: 'pointer', userSelect: 'none' }}
              >
                ID {sortCol === 'id' && (sortDir === 1 ? '▲' : '▼')}
              </th>"""
            n += 1
        elif "<th style={{ padding: '12px', textAlign: 'left' }}>Имя</th>" in lines[i]:
            lines[i] = """              <th
                onClick={() => { setSortCol('name'); setSortDir(d => sortCol === 'name' ? -d : 1) }}
                style={{ padding: '12px', textAlign: 'left', cursor: 'pointer', userSelect: 'none' }}
              >
                Имя {sortCol === 'name' && (sortDir === 1 ? '▲' : '▼')}
              </th>"""
            n += 1
        elif "<th style={{ padding: '12px', textAlign: 'left' }}>IP:Порт</th>" in lines[i]:
            lines[i] = """              <th
                onClick={() => { setSortCol('ipaddress'); setSortDir(d => sortCol === 'ipaddress' ? -d : 1) }}
                style={{ padding: '12px', textAlign: 'left', cursor: 'pointer', userSelect: 'none' }}
              >
                IP:Порт {sortCol === 'ipaddress' && (sortDir === 1 ? '▲' : '▼')}
              </th>"""
            n += 1

    if n > 3:
        print("  [OK] заголовки ID/Имя/IP сделаны кликабельными")
    else:
        print(f"  [WARN] заменено только {n} заголовков (ожидалось 3)")

    # 5. Заменяем cameras.map на visibleCameras.map
    for i in range(len(lines)):
        if "{cameras.map((camera) => (" in lines[i]:
            lines[i] = lines[i].replace("cameras.map", "visibleCameras.map")
            n += 1
            print("  [OK] cameras.map → visibleCameras.map")
            break

    # 6. Добавляем пустое состояние после tbody
    tbody_end_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if "</tbody>" in lines[i]:
            tbody_end_idx = i
            break

    if tbody_end_idx:
        empty_state = """
            {visibleCameras.length === 0 && (
              <tr>
                <td colSpan="5" style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                  {search || enabledFilter !== 'all' ? (
                    <>
                      Ничего не найдено
                      {search && <> по запросу <strong>"{search}"</strong></>}
                      <br />
                      <button
                        onClick={() => { setSearch(''); setEnabledFilter('all') }}
                        style={{
                          marginTop: '12px', padding: '6px 16px', background: '#334155',
                          border: 'none', borderRadius: '6px', color: '#e0e3e8',
                          fontSize: '0.75rem', cursor: 'pointer',
                        }}
                      >
                        Сбросить фильтры
                      </button>
                    </>
                  ) : (
                    'Нет камер'
                  )}
                </td>
              </tr>
            )}"""
        lines.insert(tbody_end_idx, empty_state)
        n += 1
        print("  [OK] пустое состояние добавлено")

    c = "\n".join(lines)

    # Проверка синтаксиса (базовая)
    if "useMemo" not in c:
        print("  [FAIL] useMemo не найден в итоговом файле")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    f.write_text(c, encoding="utf-8")
    print(f"  [OK] файл сохранён (изменений: {n})")

    print()
    print("=" * 76)
    print("✅ PATCH-219 готов! Сборка + проверка:")
    print()
    print(f"  cd {root}/frontend && npm run build")
    print()
    print("Откройте /cameras (Ctrl+F5):")
    print("  • Панель поиска + select фильтра + счётчик 'Найдено: N из 274'")
    print("  • Клик по ID/Имя/IP — сортировка со стрелками ▲/▼")
    print("  • Комбинация: поиск '210' + фильтр 'Включённые' + сортировка по IP")
    print("  • Пустое состояние: 'Ничего не найдено по запросу \"...\"' + кнопка сброса")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat(cameras): search + filter + sort by ID/name/IP (PATCH-219)" \\')
    print('  -m "panel: search input + enabled filter + counter + reset button" \\')
    print('  -m "clickable headers: ID/Name/IP with ▲/▼ indicators" \\')
    print('  -m "useMemo: visibleCameras = search ∩ filter → sort" \\')
    print('  -m "empty state with reset button"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()