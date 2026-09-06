#!/usr/bin/env python3
"""
165. update_scripts/165_aspect_render_final.py
----------------------------------------------------------------------------
Точная версия PATCH-162/163/164 с якорями из актуальных файлов.
aspect_ratio набора влияет на рендер ячеек.

ЗАПУСК: python update_scripts/165_aspect_render_final.py
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
    print("165: aspect_ratio влияет на рендер (точная версия)")
    print("=" * 76)
    print()

    # ====================================================================
    # 1. SetsPage.jsx
    # ====================================================================
    print("--- SetsPage.jsx ---")
    b = sets_jsx.with_suffix(".jsx.bak-165")
    b.write_text(sets_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    content = sets_jsx.read_text(encoding="utf-8")

    if "PATCH-165" in content:
        print("  [OK] Уже применён")
    else:
        n = 0

        # 1a. gridTemplateColumns
        old = "      gridTemplateColumns: `repeat(${maxCols}, 1fr)`,"
        new = "      gridTemplateColumns: `repeat(${maxCols}, minmax(0, 1fr))`,  // PATCH-165"
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] колонки minmax(0,1fr)")

        # 1b. Удаляем gridTemplateRows
        old = "      gridTemplateRows: `repeat(${maxRows}, 1fr)`\n"
        if old in content:
            content = content.replace(old, "", 1); n += 1
            print("  [OK] строки auto (удалено)")

        # 1c. cellAspect
        old = "  const maxRows = activeSet ? activeSet.max_rows : 1\n"
        new = "  const maxRows = activeSet ? activeSet.max_rows : 1\n  // PATCH-165: пропорции ячейки из формата набора\n  const cellAspect = ((activeSet && activeSet.aspect_ratio) || '16:9').replace(':', ' / ')\n"
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] cellAspect")

        # 1d. aspectRatio на ячейках
        old = """          className={'sets-cell'+(cam ? ' has-cam' : '')+
            (dropTarget===idx ? ' drag-over' : '')}
          onDragOver={(e)=>{handleDragOver(e);setDropTarget(idx)}}"""
        new = """          className={'sets-cell'+(cam ? ' has-cam' : '')+
            (dropTarget===idx ? ' drag-over' : '')}
          style={{aspectRatio: cellAspect}}
          onDragOver={(e)=>{handleDragOver(e);setDropTarget(idx)}}"""
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] aspectRatio на ячейках")

        if n == 4 and content.count('{') == content.count('}'):
            sets_jsx.write_text(content, encoding="utf-8")
            print("  [OK] Сохранено")
        else:
            print(f"  [FAIL] {n}/4 — откат")
            sets_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

    # ====================================================================
    # 2. sets.css
    # ====================================================================
    css = sets_css.read_text(encoding="utf-8")
    if "PATCH-165" not in css:
        css += "\n/* PATCH-165: строки auto не растягиваются */\n.sets-grid { align-content: start; overflow: auto; }\n"
        sets_css.write_text(css, encoding="utf-8")
        print("  [OK] sets.css")

    # ====================================================================
    # 3. MonitorPage.jsx
    # ====================================================================
    print()
    print("--- MonitorPage.jsx ---")
    b = monitor_jsx.with_suffix(".jsx.bak-165")
    b.write_text(monitor_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    content = monitor_jsx.read_text(encoding="utf-8")

    if "PATCH-165" in content:
        print("  [OK] Уже применён")
    else:
        m = 0

        # 3a. gridTemplateColumns
        old = "    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, 1fr)`"
        new = "    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, minmax(0, 1fr))`  // PATCH-165"
        if old in content:
            content = content.replace(old, new, 1); m += 1
            print("  [OK] gridStyle колонки")

        # 3b. Удаляем блок gridTemplateRows
        old = """  if (setData && setData.max_rows > 0) {
    gridStyle.gridTemplateRows = `repeat(${setData.max_rows}, 1fr)`
  }
"""
        if old in content:
            content = content.replace(old, "", 1); m += 1
            print("  [OK] gridStyle строки (удалено)")

        # 3c. cellAspect
        old = "const hasFixedGrid = setData && setData.max_columns > 0 && setData.max_rows > 0"
        new = "const hasFixedGrid = setData && setData.max_columns > 0 && setData.max_rows > 0\n  // PATCH-165: пропорции ячейки из формата набора\n  const cellAspect = ((setData && setData.aspect_ratio) || '16:9').replace(':', ' / ')\n"
        if old in content:
            content = content.replace(old, new, 1); m += 1
            print("  [OK] cellAspect")

        # 3d. CameraCard в .aspect-wrap
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
                  <div key={camera.id} className="aspect-wrap" style={{aspectRatio: cellAspect}}>
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

        # 3e. CameraEmpty в .aspect-wrap
        old = """            {Array.from({ length: emptyCount }).map((_, i) => (
              <CameraEmpty key={`empty-${i}`} index={i} />
            ))}"""
        new = """            {Array.from({ length: emptyCount }).map((_, i) => (
              <div key={`empty-${i}`} className="aspect-wrap" style={{aspectRatio: cellAspect}}>
                <CameraEmpty index={i} />
              </div>
            ))}"""
        if old in content:
            content = content.replace(old, new, 1); m += 1
            print("  [OK] CameraEmpty в .aspect-wrap")

        if m == 5 and content.count('{') == content.count('}'):
            monitor_jsx.write_text(content, encoding="utf-8")
            print("  [OK] Сохранено")
        else:
            print(f"  [FAIL] {m}/5 — откат")
            monitor_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

    # ====================================================================
    # 4. CSS монитора
    # ====================================================================
    css = layout_css.read_text(encoding="utf-8")
    if "PATCH-165" not in css:
        css += "\n/* PATCH-165: строки auto, скролл внутри */\n.fullscreen-grid { align-content: start; overflow: auto; }\n"
        layout_css.write_text(css, encoding="utf-8")
        print("  [OK] layout.css")

    css = camera_css.read_text(encoding="utf-8")
    if "aspect-wrap" not in css:
        css += """
/* PATCH-165: обёртка ячейки с пропорциями набора */
.aspect-wrap {
  min-width: 0;
  min-height: 0;
  position: relative;
  overflow: hidden;
  background: #000;
}
.aspect-wrap .camera-card { height: 100%; width: 100%; }
"""
        camera_css.write_text(css, encoding="utf-8")
        print("  [OK] camera.css")

    print()
    print("=" * 76)
    print("✅ Готово! aspect_ratio теперь влияет на рендер:")
    print()
    print("  • 16:9 → широкие низкие ячейки")
    print("  • 4:3  → более высокие ячейки")
    print("  • Поток 16:9 в ячейке 4:3 → чёрные полосы (object-fit: contain)")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()