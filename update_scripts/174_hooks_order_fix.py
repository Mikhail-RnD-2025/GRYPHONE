#!/usr/bin/env python3
"""
174. update_scripts/174_hooks_order_fix.py
----------------------------------------------------------------------------
Фикс чёрной страницы /sets: хук useFitCellSize вызывается ДО if (loading)
return — соблюдение Rules of Hooks.

ЗАПУСК: python update_scripts/174_hooks_order_fix.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    sets_jsx = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"

    print("=" * 76)
    print("174: Rules of Hooks — хук до условного return")
    print("=" * 76)
    print()

    b = sets_jsx.with_suffix(".jsx.bak-174")
    b.write_text(sets_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    c = sets_jsx.read_text(encoding="utf-8")

    if "PATCH-174" in c:
        print("  [OK] Уже применён")
        return

    old = """  if (loading) return <div className="sets-loading">Загрузка...</div>

  const gridCameras = (activeSet ? activeSet.camera_ids : [])
    .map(id => cameras.find(c => c.id === id)).filter(Boolean)
  const maxCols = activeSet ? activeSet.max_columns : 1
  const maxRows = activeSet ? activeSet.max_rows : 1
  // PATCH-173: пропорции и размер ячейки под окно
  const aspectNum = ((activeSet && activeSet.aspect_ratio) === '4:3') ? 4 / 3 : 16 / 9
  const [gridRef, cellSize] = useFitCellSize(maxCols, maxRows, aspectNum)"""

    new = """  // PATCH-174: хуки строго ДО условного return (Rules of Hooks)
  const maxCols = activeSet ? activeSet.max_columns : 1
  const maxRows = activeSet ? activeSet.max_rows : 1
  const aspectNum = ((activeSet && activeSet.aspect_ratio) === '4:3') ? 4 / 3 : 16 / 9
  const [gridRef, cellSize] = useFitCellSize(maxCols, maxRows, aspectNum)

  if (loading) return <div className="sets-loading">Загрузка...</div>

  const gridCameras = (activeSet ? activeSet.camera_ids : [])
    .map(id => cameras.find(c => c.id === id)).filter(Boolean)"""

    if old in c:
        c = c.replace(old, new, 1)
        if c.count('{') == c.count('}'):
            sets_jsx.write_text(c, encoding="utf-8")
            print("  [OK] хук перенесён до if (loading)")
        else:
            print("  [FAIL] скобки — откат")
            sets_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)
    else:
        print("  [FAIL] якорь не найден — откат")
        sets_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Страница /sets откроется.")
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print("cd /c/GRYPHONE_PROJ/v26")
    print("git add -A")
    print('git commit -m "fix: black /sets page - hook before conditional return (PATCH-174)" \\')
    print('  -m "useFitCellSize moved above if (loading) return (Rules of Hooks)"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()