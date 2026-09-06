#!/usr/bin/env python3
"""
162. update_scripts/162_aspect_ratio_render.py
----------------------------------------------------------------------------
aspect_ratio набора теперь влияет на рендер ячеек:
  • SetsPage: колонки minmax(0,1fr), строки auto, aspect-ratio на ячейках
  • MonitorPage: то же + обёртка .aspect-wrap для CameraCard/CameraEmpty
  • CSS: align-content: start + overflow: auto (сетка не раздувается)

ЗАПУСК: python update_scripts/162_aspect_ratio_render.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    sets_jsx = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"
    monitor_jsx = project_root / "frontend" / "src" / "pages" / "MonitorPage.jsx"
    sets_css = project_root / "frontend" / "src" / "styles" / "sets.css"
    camera_css = project_root / "frontend" / "src" / "styles" / "camera.css"
    layout_css = project_root / "frontend" / "src" / "styles" / "layout.css"

    print("=" * 76)
    print("162: aspect_ratio влияет на рендер ячеек")
    print("=" * 76)
    print()

    # ====================================================================
    # 1. SetsPage.jsx
    # ====================================================================
    print("--- SetsPage.jsx ---")
    b = sets_jsx.with_suffix(".jsx.bak-162")
    b.write_text(sets_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    content = sets_jsx.read_text(encoding="utf-8")
    n = 0

    old = """            style={{
              gridTemplateColumns: `repeat(${maxCols}, 1fr)`,
              gridTemplateRows: `repeat(${maxRows}, 1fr)`
            }}"""
    new = """            style={{
              gridTemplateColumns: `repeat(${maxCols}, minmax(0, 1fr))`  // PATCH-162
            }}"""
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] колонки minmax(0,1fr), строки auto")

    old = """  const maxRows = activeSet ? activeSet.max_rows : 1"""
    new = """  const maxRows = activeSet ? activeSet.max_rows : 1
  // PATCH-162: пропорции ячейки из формата набора
  const cellAspect = ((activeSet && activeSet.aspect_ratio) || '16:9').replace(':', ' / ')"""
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] cellAspect")

    old = """                  <div
                    key={idx}
                    className={'sets-cell' + (cam ? ' has-cam' : '') +
                      (dropTarget === idx ? ' drag-over' : '')}
                    onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}"""
    new = """                  <div
                    key={idx}
                    className={'sets-cell' + (cam ? ' has-cam' : '') +
                      (dropTarget === idx ? ' drag-over' : '')}
                    style={{ aspectRatio: cellAspect }}
                    onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}"""
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] aspectRatio на ячейках")

    if n == 3 and content.count('{') == content.count('}'):
        sets_jsx.write_text(content, encoding="utf-8")
        print("  [OK] Сохранено")
    else:
        print(f"  [FAIL] {n}/3 — откат")
        sets_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # ====================================================================
    # 2. sets.css
    # ====================================================================
    print()
    print("--- sets.css ---")
    css = sets_css.read_text(encoding="utf-8")
    if "PATCH-162" not in css:
        old = """  overflow: auto;  /* PATCH-152: скролл при необходимости */
}"""
        new = """  overflow: auto;
  align-content: start;  /* PATCH-162: строки auto не растягиваются */
}"""
        if old in css:
            sets_css.write_text(css.replace(old, new, 1), encoding="utf-8")
            print("  [OK] align-content: start")
        else:
            print("  [WARN] .sets-grid не найден")

    # ====================================================================
    # 3. MonitorPage.jsx
    # ====================================================================
    print()
    print("--- MonitorPage.jsx ---")
    b = monitor_jsx.with_suffix(".jsx.bak-162")
    b.write_text(monitor_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    content = monitor_jsx.read_text(encoding="utf-8")
    m = 0

    old = """  if (setData && setData.max_columns > 0) {
    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, 1fr)`
  } else {
    gridStyle.gridTemplateColumns = 'repeat(auto-fill, minmax(280px, 1fr))'
  }
  if (setData && setData.max_rows > 0) {
    gridStyle.gridTemplateRows = `repeat(${setData.max_rows}, 1fr)`
  }"""
    new = """  if (setData && setData.max_columns > 0) {
    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, minmax(0, 1fr))`  // PATCH-162
  } else {
    gridStyle.gridTemplateColumns = 'repeat(auto-fill, minmax(280px, 1fr))'
  }
  // PATCH-162: строки auto, пропорции ячейки из формата набора
  const cellAspect = ((setData && setData.aspect_ratio) || '16:9').replace(':', ' / ')"""
    if old in content:
        content = content.replace(old, new, 1); m += 1
        print("  [OK] gridStyle: minmax(0,1fr) + cellAspect")

    old = """                return (
                  <CameraCard
                    key={camera.id}
                    camera={camera}
                    status={status}
                    onContextMenu={handleContextMenu}
                    onFullscreen={handleFullscreen}
                  />
                )"""
    new = """                return (
                  <div key={camera.id} className="aspect-wrap" style={{ aspectRatio: cellAspect }}>
                    <CameraCard
                      camera={camera}
                      status={status}
                      onContextMenu={handleContextMenu}
                      onFullscreen={handleFullscreen}
                    />
                  </div>
                )"""
    if old in content:
        content = content.replace(old, new, 1); m += 1
        print("  [OK] CameraCard в .aspect-wrap")

    old = """            {Array.from({ length: emptyCount }).map((_, i) => (
              <CameraEmpty key={`empty-${i}`} index={i} />
            ))}"""
    new = """            {Array.from({ length: emptyCount }).map((_, i) => (
              <div key={`empty-${i}`} className="aspect-wrap" style={{ aspectRatio: cellAspect }}>
                <CameraEmpty index={i} />
              </div>
            ))}"""
    if old in content:
        content = content.replace(old, new, 1); m += 1
        print("  [OK] CameraEmpty в .aspect-wrap")

    if m == 3 and content.count('{') == content.count('}'):
        monitor_jsx.write_text(content, encoding="utf-8")
        print("  [OK] Сохранено")
    else:
        print(f"  [FAIL] {m}/3 — откат")
        monitor_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # ====================================================================
    # 4. CSS для монитора
    # ====================================================================
    print()
    print("--- layout.css / camera.css ---")
    css = layout_css.read_text(encoding="utf-8")
    if "PATCH-162" not in css:
        old = """.fullscreen-grid {
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
  display: grid;
  gap: 2px;
  background: #0b0d10;
}"""
        new = """.fullscreen-grid {
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
  display: grid;
  gap: 2px;
  background: #0b0d10;
  align-content: start;  /* PATCH-162 */
  overflow: auto;        /* PATCH-162 */
}"""
        if old in css:
            layout_css.write_text(css.replace(old, new, 1), encoding="utf-8")
            print("  [OK] .fullscreen-grid: align-content + overflow")

    css = camera_css.read_text(encoding="utf-8")
    if "aspect-wrap" not in css:
        css += """
/* PATCH-162: обёртка ячейки с пропорциями набора */
.aspect-wrap {
  min-width: 0;
  min-height: 0;
  position: relative;
  overflow: hidden;
  background: #000;
}
.aspect-wrap .camera-card {
  height: 100%;
  width: 100%;
}
"""
        camera_css.write_text(css, encoding="utf-8")
        print("  [OK] .aspect-wrap в camera.css")

    print()
    print("=" * 76)
    print("✅ Готово! aspect_ratio теперь влияет на рендер:")
    print()
    print("  • 16:9 → широкие низкие ячейки")
    print("  • 4:3  → более высокие ячейки")
    print("  • Поток 16:9 в ячейке 4:3 → чёрные полосы (object-fit: contain)")
    print("  • Не умещается → скролл внутри сетки")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()