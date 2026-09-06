#!/usr/bin/env python3
"""
163. update_scripts/163_aspect_render_fixed.py
----------------------------------------------------------------------------
Исправленная версия PATCH-162: aspect_ratio влияет на рендер ячеек.
  • SetsPage: колонки minmax(0,1fr), строки auto, aspect-ratio на ячейках
  • MonitorPage: то же + обёртка .aspect-wrap
  • CSS дописывается в конец файлов (касскад, без точных якорей)

ЗАПУСК: python update_scripts/163_aspect_render_fixed.py
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
    print("163: aspect_ratio влияет на рендер (исправленная версия 162)")
    print("=" * 76)
    print()

    # ====================================================================
    # 1. SetsPage.jsx
    # ====================================================================
    print("--- SetsPage.jsx ---")
    b = sets_jsx.with_suffix(".jsx.bak-163")
    b.write_text(sets_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    content = sets_jsx.read_text(encoding="utf-8")

    if "PATCH-163" in content:
        print("  [OK] Уже применён")
    else:
        n = 0

        # 1a. style сетки (с фолбэком на вариант без комментария)
        variants = [
            """            style={{
              gridTemplateColumns: `repeat(${maxCols}, 1fr)`,
              gridTemplateRows: `repeat(${maxRows}, 1fr)`  // PATCH-149: как в мониторинге
            }}""",
            """            style={{
              gridTemplateColumns: `repeat(${maxCols}, 1fr)`,
              gridTemplateRows: `repeat(${maxRows}, 1fr)`
            }}""",
        ]
        new = """            style={{
              gridTemplateColumns: `repeat(${maxCols}, minmax(0, 1fr))`  // PATCH-163
            }}"""
        for old in variants:
            if old in content:
                content = content.replace(old, new, 1); n += 1
                print("  [OK] колонки minmax(0,1fr), строки auto")
                break

        # 1b. cellAspect
        old = """  const maxRows = activeSet ? activeSet.max_rows : 1"""
        new2 = """  const maxRows = activeSet ? activeSet.max_rows : 1
  // PATCH-163: пропорции ячейки из формата набора
  const cellAspect = ((activeSet && activeSet.aspect_ratio) || '16:9').replace(':', ' / ')"""
        if old in content:
            content = content.replace(old, new2, 1); n += 1
            print("  [OK] cellAspect")

        # 1c. aspectRatio на ячейках
        old = """                  <div
                    key={idx}
                    className={'sets-cell' + (cam ? ' has-cam' : '') +
                      (dropTarget === idx ? ' drag-over' : '')}
                    onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}"""
        new3 = """                  <div
                    key={idx}
                    className={'sets-cell' + (cam ? ' has-cam' : '') +
                      (dropTarget === idx ? ' drag-over' : '')}
                    style={{ aspectRatio: cellAspect }}
                    onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}"""
        if old in content:
            content = content.replace(old, new3, 1); n += 1
            print("  [OK] aspectRatio на ячейках")

        if n == 3 and content.count('{') == content.count('}'):
            sets_jsx.write_text(content, encoding="utf-8")
            print("  [OK] Сохранено")
        else:
            print(f"  [FAIL] {n}/3 — откат")
            sets_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

    # ====================================================================
    # 2. sets.css — дописываем в конец (касскад)
    # ====================================================================
    print()
    print("--- sets.css ---")
    css = sets_css.read_text(encoding="utf-8")
    if "PATCH-163" not in css:
        css += """
/* PATCH-163: строки auto не растягиваются, скролл внутри */
.sets-grid { align-content: start; overflow: auto; }
"""
        sets_css.write_text(css, encoding="utf-8")
        print("  [OK] .sets-grid: align-content: start (дописано)")
    else:
        print("  [OK] Уже есть")

    # ====================================================================
    # 3. MonitorPage.jsx
    # ====================================================================
    print()
    print("--- MonitorPage.jsx ---")
    b = monitor_jsx.with_suffix(".jsx.bak-163")
    b.write_text(monitor_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    content = monitor_jsx.read_text(encoding="utf-8")

    if "PATCH-163" in content:
        print("  [OK] Уже применён")
    else:
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
    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, minmax(0, 1fr))`  // PATCH-163
  } else {
    gridStyle.gridTemplateColumns = 'repeat(auto-fill, minmax(280px, 1fr))'
  }
  // PATCH-163: строки auto, пропорции ячейки из формата набора
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
    # 4. CSS монитора — дописываем в конец
    # ====================================================================
    print()
    print("--- layout.css / camera.css ---")
    css = layout_css.read_text(encoding="utf-8")
    if "PATCH-163" not in css:
        css += """
/* PATCH-163: строки auto, не растягиваются; скролл внутри сетки */
.fullscreen-grid { align-content: start; overflow: auto; }
"""
        layout_css.write_text(css, encoding="utf-8")
        print("  [OK] .fullscreen-grid (дописано)")

    css = camera_css.read_text(encoding="utf-8")
    if "aspect-wrap" not in css:
        css += """
/* PATCH-163: обёртка ячейки с пропорциями набора */
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
        print("  [OK] .aspect-wrap (дописано)")

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