#!/usr/bin/env python3
"""
169. update_scripts/169_grid_fit_window.py
----------------------------------------------------------------------------
Сетка вписывается в окно без скролла (обе страницы):
  • useFitCellSize: измеряет контейнер, считает ячейку по формуле
    cell = min((W - gaps) / cols, (H - gaps) / rows * ratio)
  • gridTemplateColumns: repeat(cols, ${cellW}px) — фиксированный размер
  • justify-content: center + align-content: center — поля сверху/снизу/сбоку
  • ResizeObserver пересчитывает при изменении окна

ЗАПУСК: python update_scripts/169_grid_fit_window.py
"""

import sys
from pathlib import Path


HOOK_CODE = '''// PATCH-169: расчёт размера ячейки, чтобы сетка влезала в контейнер
function useFitCellSize(cols, rows, ratio) {
  const ref = useRef(null)
  const [size, setSize] = useState({ w: 0, h: 0 })
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const calc = () => {
      const rect = el.getBoundingClientRect()
      const gap = 4
      const availW = rect.width - 16 - gap * (cols - 1)   // padding 8px*2
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


def patch_sets(jsx_file):
    print("--- SetsPage.jsx ---")
    b = jsx_file.with_suffix(".jsx.bak-169")
    b.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    c = jsx_file.read_text(encoding="utf-8")

    if "PATCH-169" in c:
        print("  [OK] Уже применён")
        return True

    n = 0

    # 1. Хук после deepClone
    old = "const deepClone = (x) => JSON.parse(JSON.stringify(x))"
    if old in c:
        c = c.replace(old, old + "\n\n" + HOOK_CODE, 1); n += 1
        print("  [OK] хук useFitCellSize добавлен")

    # 2. Вызов хука + ratio
    old = """  const cellAspect = ((activeSet && activeSet.aspect_ratio) || '16:9').replace(':', ' / ')"""
    new = """  const cellAspect = ((activeSet && activeSet.aspect_ratio) || '16:9').replace(':', ' / ')
  // PATCH-169: числовое соотношение и размер ячейки под окно
  const aspectNum = ((activeSet && activeSet.aspect_ratio) === '4:3') ? 4 / 3 : 16 / 9
  const [gridRef, cellSize] = useFitCellSize(maxCols, maxRows, aspectNum)"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] aspectNum + вызов хука")

    # 3. div сетки: ref + px-колонки
    old = """            <div
              className="sets-grid"
              style={{
                gridTemplateColumns: `repeat(${maxCols}, minmax(0, 1fr))`,  // PATCH-166
              }}"""
    new = """            <div
              ref={gridRef}
              className="sets-grid"
              style={{
                gridTemplateColumns: `repeat(${maxCols}, ${cellSize.w}px)`  // PATCH-169
              }}"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] ref + px-колонки")

    # 4. Убираем aspectRatio со style ячейки (высота теперь из grid-auto-rows)
    old = """                    style={{ aspectRatio: cellAspect }}
                    onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}"""
    new = """                    onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] aspectRatio с ячеек убран (auto-rows)")

    if n == 4 and c.count('{') == c.count('}'):
        jsx_file.write_text(c, encoding="utf-8")
        print("  [OK] Сохранено")
        return True
    print(f"  [FAIL] {n}/4 — откат")
    jsx_file.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
    return False


def patch_monitor(jsx_file):
    print()
    print("--- MonitorPage.jsx ---")
    b = jsx_file.with_suffix(".jsx.bak-169")
    b.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    c = jsx_file.read_text(encoding="utf-8")

    if "PATCH-169" in c:
        print("  [OK] Уже применён")
        return True

    m = 0

    # 1. Хук после импортов (после строки import { getCurrentSetCameras })
    old = "import { getCurrentSetCameras } from '../api'"
    if old in c:
        c = c.replace(old, old + "\n\n" + HOOK_CODE.replace("useRef", "useRef").replace("// PATCH-169", "// PATCH-169 (monitor)"), 1)
        m += 1
        print("  [OK] хук добавлен")

    # 2. aspectNum + вызов хука после hasSets
    old = "  const hasSets = setData && setData.set_id !== ''"
    new = """  const hasSets = setData && setData.set_id !== ''
  // PATCH-169: числовое соотношение и размер ячейки под окно
  const aspectNum = ((setData && setData.aspect_ratio) === '4:3') ? 4 / 3 : 16 / 9
  const maxColsM = (setData && setData.max_columns > 0) ? setData.max_columns : 4
  const maxRowsM = (setData && setData.max_rows > 0) ? setData.max_rows : 3
  const [gridRef, cellSize] = useFitCellSize(maxColsM, maxRowsM, aspectNum)"""
    if old in c:
        c = c.replace(old, new, 1); m += 1
        print("  [OK] aspectNum + вызов хука")

    # 3. gridStyle: убираем height 100% (контейнер меряется сам), px-колонки
    old = """  if (setData && setData.max_columns > 0) {
    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, minmax(0, 1fr))`  // PATCH-168
  } else {
    gridStyle.gridTemplateColumns = 'repeat(auto-fill, minmax(280px, 1fr))'
  }"""
    new = """  // PATCH-169: фиксированный размер ячейки, вписанный в окно
  if (setData && setData.max_columns > 0) {
    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, ${cellSize.w}px)`
    gridStyle.gridAutoRows = `${cellSize.h}px`
  } else {
    gridStyle.gridTemplateColumns = 'repeat(auto-fill, minmax(280px, 1fr))'
  }"""
    if old in c:
        c = c.replace(old, new, 1); m += 1
        print("  [OK] px-колонки + auto-rows")

    # 4. div fullscreen-grid: ref
    old = '        <div className="fullscreen-grid" style={gridStyle}>'
    new = '        <div ref={gridRef} className="fullscreen-grid" style={gridStyle}>'
    if old in c:
        c = c.replace(old, new, 1); m += 1
        print("  [OK] ref на fullscreen-grid")

    # 5. Убираем aspect-wrap обёртки (размер даёт grid)
    old = """              <div key={camera.id} className="aspect-wrap" style={{ aspectRatio: cellAspect }}>
                <CameraCard
                  camera={camera}
                  status={status}
                  onContextMenu={handleContextMenu}
                  onFullscreen={handleFullscreen}
                />
              </div>"""
    new = """              <CameraCard
                key={camera.id}
                camera={camera}
                status={status}
                onContextMenu={handleContextMenu}
                onFullscreen={handleFullscreen}
              />"""
    if old in c:
        c = c.replace(old, new, 1); m += 1
        print("  [OK] CameraCard без обёртки")

    old = """            <div key={`empty-${i}`} className="aspect-wrap" style={{ aspectRatio: cellAspect }}>
              <CameraEmpty index={i} />
            </div>"""
    new = """            <CameraEmpty key={`empty-${i}`} index={i} />"""
    if old in c:
        c = c.replace(old, new, 1); m += 1
        print("  [OK] CameraEmpty без обёртки")

    if m >= 5 and c.count('{') == c.count('}'):
        jsx_file.write_text(c, encoding="utf-8")
        print("  [OK] Сохранено")
        return True
    print(f"  [FAIL] {m} замен — откат")
    jsx_file.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
    return False


def main():
    project_root = Path.cwd()
    sets_css = project_root / "frontend" / "src" / "styles" / "sets.css"
    layout_css = project_root / "frontend" / "src" / "styles" / "layout.css"

    print("=" * 76)
    print("169: Сетка вписывается в окно без скролла")
    print("=" * 76)
    print()

    ok1 = patch_sets(project_root / "frontend" / "src" / "pages" / "SetsPage.jsx")
    ok2 = patch_monitor(project_root / "frontend" / "src" / "pages" / "MonitorPage.jsx")

    # CSS: центрирование + скрытие скролла
    print()
    print("--- CSS ---")
    css = sets_css.read_text(encoding="utf-8")
    if "PATCH-169" not in css:
        css += """
/* PATCH-169: сетка центрируется, без скролла */
.sets-grid {
  justify-content: center;
  align-content: center;
  overflow: hidden;
}
"""
        sets_css.write_text(css, encoding="utf-8")
        print("  [OK] sets.css: center + hidden")

    css = layout_css.read_text(encoding="utf-8")
    if "PATCH-169" not in css:
        css += """
/* PATCH-169: сетка центрируется, без скролла */
.fullscreen-grid {
  justify-content: center;
  align-content: center;
  overflow: hidden;
}
"""
        layout_css.write_text(css, encoding="utf-8")
        print("  [OK] layout.css: center + hidden")

    if not (ok1 and ok2):
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Сетка вписана в окно:")
    print("  • пропорции 16:9 / 4:3 сохраняются")
    print("  • зазоры между ячейками сохранены (4px / 2px)")
    print("  • свободное место — поля сверху/снизу (центрирование)")
    print("  • скролла нет; при ресайзе окна — пересчёт")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()