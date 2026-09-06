#!/usr/bin/env python3
"""
172. update_scripts/172_black_screen_fix.py
----------------------------------------------------------------------------
Фикс чёрного экрана:
  • хук useFitCellSize: callback-ref (setNode) — observer цепляется,
    когда div ПОЯВЛЯЕТСЯ в DOM (после loading / условия)
  • fallback: пока размер не вычислен — колонки minmax(0,1fr), не 0px

ЗАПУСК: python update_scripts/172_black_screen_fix.py
"""

import sys
from pathlib import Path

NEW_HOOK = '''// PATCH-172: callback-ref — работает при отложенном рендере сетки
function useFitCellSize(cols, rows, ratio) {
  const [node, setNode] = useState(null)
  const [size, setSize] = useState({ w: 0, h: 0 })
  useEffect(() => {
    if (!node) return
    const calc = () => {
      const rect = node.getBoundingClientRect()
      const gap = 4
      const availW = rect.width - 16 - gap * (cols - 1)
      const availH = rect.height - 16 - gap * (rows - 1)
      let w = Math.min(availW / cols, (availH / rows) * ratio)
      w = Math.max(60, Math.floor(w))
      setSize({ w, h: Math.floor(w / ratio) })
    }
    calc()
    const ro = new ResizeObserver(calc)
    ro.observe(node)
    return () => ro.disconnect()
  }, [node, cols, rows, ratio])
  return [setNode, size]
}
'''


def replace_hook(content, tag):
    start = content.find("function useFitCellSize")
    if start == -1:
        return content, False
    cs = content.rfind("//", 0, start)
    if cs == -1 or start - cs > 300:
        cs = start
    end = content.find("\n}\n", start)
    if end == -1:
        return content, False
    end += len("\n}\n")
    return content[:cs] + NEW_HOOK + content[end:], True


def main():
    project_root = Path.cwd()
    sets_jsx = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"
    monitor_jsx = project_root / "frontend" / "src" / "pages" / "MonitorPage.jsx"

    print("=" * 76)
    print("172: Фикс чёрного экрана (callback-ref + fallback)")
    print("=" * 76)
    print()

    # --- SetsPage ---
    print("--- SetsPage.jsx ---")
    b = sets_jsx.with_suffix(".jsx.bak-172")
    b.write_text(sets_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    c = sets_jsx.read_text(encoding="utf-8")

    if "PATCH-172" in c:
        print("  [OK] Уже применён")
    else:
        n = 0
        c, ok = replace_hook(c, "sets")
        if ok:
            n += 1
            print("  [OK] хук заменён на callback-ref версию")

        old = """              style={{
                gridTemplateColumns: `repeat(${maxCols}, ${cellSize.w}px)`,  // PATCH-171
                gridAutoRows: `${cellSize.h}px`
              }}"""
        new = """              style={{
                gridTemplateColumns: cellSize.w
                  ? `repeat(${maxCols}, ${cellSize.w}px)`
                  : `repeat(${maxCols}, minmax(0, 1fr))`,  // PATCH-172
                gridAutoRows: cellSize.h ? `${cellSize.h}px` : undefined
              }}"""
        if old in c:
            c = c.replace(old, new, 1); n += 1
            print("  [OK] fallback minmax(0,1fr) пока нет размера")

        if n == 2 and c.count('{') == c.count('}'):
            sets_jsx.write_text(c, encoding="utf-8")
            print("  [OK] Сохранено")
        else:
            print(f"  [FAIL] {n}/2 — откат")
            sets_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

    # --- MonitorPage ---
    print()
    print("--- MonitorPage.jsx ---")
    b = monitor_jsx.with_suffix(".jsx.bak-172")
    b.write_text(monitor_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    c = monitor_jsx.read_text(encoding="utf-8")

    if "PATCH-172" in c:
        print("  [OK] Уже применён")
    else:
        m = 0
        c, ok = replace_hook(c, "monitor")
        if ok:
            m += 1
            print("  [OK] хук заменён на callback-ref версию")

        old = """  if (setData && setData.max_columns > 0) {
    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, ${cellSize.w}px)`
    gridStyle.gridAutoRows = `${cellSize.h}px`
  } else {"""
        new = """  if (setData && setData.max_columns > 0) {
    gridStyle.gridTemplateColumns = cellSize.w
      ? `repeat(${setData.max_columns}, ${cellSize.w}px)`
      : `repeat(${setData.max_columns}, minmax(0, 1fr))`  // PATCH-172
    if (cellSize.h) gridStyle.gridAutoRows = `${cellSize.h}px`
  } else {"""
        if old in c:
            c = c.replace(old, new, 1); m += 1
            print("  [OK] fallback minmax(0,1fr) пока нет размера")

        if m == 2 and c.count('{') == c.count('}'):
            monitor_jsx.write_text(c, encoding="utf-8")
            print("  [OK] Сохранено")
        else:
            print(f"  [FAIL] {m}/2 — откат")
            monitor_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Чёрный экран устранён:")
    print("  • observer цепляется когда div появляется в DOM")
    print("  • до расчёта — обычные 1fr колонки (не 0px)")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит (я прочитаю его на GitHub):")
    print()
    print("cd /c/GRYPHONE_PROJ/v26")
    print("git add -A")
    print('git commit -m "fix: black screen - callback ref in useFitCellSize + 1fr fallback (PATCH-172)" \\')
    print('  -m "hook now attaches ResizeObserver when grid div appears in DOM (after loading)" \\')
    print('  -m "until size computed, columns use minmax(0,1fr) instead of 0px" \\')
    print('  -m "also includes PATCH-166..171: aspect_ratio render + fit-to-window grids"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()