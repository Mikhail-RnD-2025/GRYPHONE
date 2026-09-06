#!/usr/bin/env python3
"""
171. update_scripts/171_sets_fit_and_import_fix.py
----------------------------------------------------------------------------
  • SetsPage: fit-to-window (хук + px-колонки + autoRows) — точные якоря
  • MonitorPage: добавляет useRef в импорт (баг PATCH-169)

ЗАПУСК: python update_scripts/171_sets_fit_and_import_fix.py
"""

import sys
from pathlib import Path

HOOK = '''
// PATCH-171: расчёт размера ячейки, чтобы сетка влезала в контейнер
function useFitCellSize(cols, rows, ratio) {
  const ref = useRef(null)
  const [size, setSize] = useState({ w: 0, h: 0 })
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const calc = () => {
      const rect = el.getBoundingClientRect()
      const gap = 4
      const availW = rect.width - 16 - gap * (cols - 1)
      const availH = rect.height - 16 - gap * (rows - 1)
      let w = Math.min(availW / cols, (availH / rows) * ratio)
      w = Math.max(60, Math.floor(w))
      setSize({ w, h: Math.floor(w / ratio) })
    }
    calc()
    const ro = new ResizeObserver(calc)
    ro.observe(el)
    return () => ro.disconnect()
  }, [cols, rows, ratio])
  return [ref, size]
}
'''


def main():
    project_root = Path.cwd()
    sets_jsx = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"
    monitor_jsx = project_root / "frontend" / "src" / "pages" / "MonitorPage.jsx"

    print("=" * 76)
    print("171: SetsPage fit-to-window + фикс импорта useRef")
    print("=" * 76)
    print()

    # ====================================================================
    # SetsPage.jsx
    # ====================================================================
    print("--- SetsPage.jsx ---")
    b = sets_jsx.with_suffix(".jsx.bak-171")
    b.write_text(sets_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    c = sets_jsx.read_text(encoding="utf-8")

    if "PATCH-171" in c:
        print("  [OK] Уже применён")
    else:
        n = 0

        old = "const deepClone = (x) => JSON.parse(JSON.stringify(x))"
        if old in c and "useFitCellSize" not in c:
            c = c.replace(old, old + HOOK, 1); n += 1
            print("  [OK] хук useFitCellSize")

        old = "  const maxRows = activeSet ? activeSet.max_rows : 1"
        new = """  const maxRows = activeSet ? activeSet.max_rows : 1
  // PATCH-171: пропорции и размер ячейки под окно
  const cellAspect = ((activeSet && activeSet.aspect_ratio) || '16:9').replace(':', ' / ')
  const aspectNum = ((activeSet && activeSet.aspect_ratio) === '4:3') ? 4 / 3 : 16 / 9
  const [gridRef, cellSize] = useFitCellSize(maxCols, maxRows, aspectNum)"""
        if old in c:
            c = c.replace(old, new, 1); n += 1
            print("  [OK] cellAspect + aspectNum + хук")

        old = """            <div
              className="sets-grid"
              style={{
                gridTemplateColumns: `repeat(${maxCols}, 1fr)`,
                gridTemplateRows: `repeat(${maxRows}, 1fr)`
              }}"""
        new = """            <div
              ref={gridRef}
              className="sets-grid"
              style={{
                gridTemplateColumns: `repeat(${maxCols}, ${cellSize.w}px)`,  // PATCH-171
                gridAutoRows: `${cellSize.h}px`
              }}"""
        if old in c:
            c = c.replace(old, new, 1); n += 1
            print("  [OK] ref + px-колонки + autoRows")
        else:
            print("  [FAIL] якорь div sets-grid не найден")

        if n == 3 and c.count('{') == c.count('}'):
            sets_jsx.write_text(c, encoding="utf-8")
            print("  [OK] Сохранено")
        else:
            print(f"  [FAIL] {n}/3 — откат")
            sets_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

    # ====================================================================
    # MonitorPage.jsx
    # ====================================================================
    print()
    print("--- MonitorPage.jsx ---")
    c = monitor_jsx.read_text(encoding="utf-8")
    old = "import { useState, useEffect, useCallback } from 'react'"
    new = "import { useState, useEffect, useCallback, useRef } from 'react'  // PATCH-171"
    if old in c:
        monitor_jsx.write_text(c.replace(old, new, 1), encoding="utf-8")
        print("  [OK] useRef добавлен в импорт")
    elif "useRef } from 'react'" in c:
        print("  [OK] useRef уже импортирован")
    else:
        print("  [WARN] импорт react не найден — проверьте вручную")

    print()
    print("=" * 76)
    print("✅ Готово!")
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print()
    print("Проверка:")
    print("  • Наборы: сетка вписана, без скролла, центрирована")
    print("  • 4:3 → ячейки выше; 16:9 → шире")
    print("  • Мониторинг: открывается без ошибки, сетка вписана")
    print("=" * 76)
    print()
    # ============================================================
    # БЛОК ДЛЯ КОММИТА (скопируйте и выполните после проверки)
    # ============================================================
    print("📦 ПОСЛЕ ПРОВЕРКИ — выполните:")
    print()
    print("cd /c/GRYPHONE_PROJ/v26")
    print("git add -A")
    print('git commit -m "feat: aspect_ratio render + grid fit-to-window (PATCH-166..171)" \\')
    print('  -m "PATCH-166: SetsPage cell aspectRatio, minmax(0,1fr) columns, auto rows" \\')
    print('  -m "PATCH-167: MonitorPage same + .aspect-wrap for CameraCard/CameraEmpty" \\')
    print('  -m "PATCH-168: MonitorPage with accurate anchors" \\')
    print('  -m "PATCH-169: useFitCellSize hook + px grid + center + overflow:hidden" \\')
    print('  -m "PATCH-170: SetsPage fit complete" \\')
    print('  -m "PATCH-171: SetsPage fit final + MonitorPage useRef import fix" \\')
    print('  -m "Result: grid fits window without scroll, preserves aspect_ratio (16:9/4:3) and gaps"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()