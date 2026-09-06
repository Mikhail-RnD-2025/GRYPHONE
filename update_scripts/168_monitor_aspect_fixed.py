#!/usr/bin/env python3
"""
168. update_scripts/168_monitor_aspect_fixed.py
----------------------------------------------------------------------------
aspect_ratio на главном экране (исправленная версия PATCH-167)
с точными якорями из реального MonitorPage.jsx.

ЗАПУСК: python update_scripts/168_monitor_aspect_fixed.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    monitor_jsx = project_root / "frontend" / "src" / "pages" / "MonitorPage.jsx"
    layout_css = project_root / "frontend" / "src" / "styles" / "layout.css"
    camera_css = project_root / "frontend" / "src" / "styles" / "camera.css"

    print("=" * 76)
    print("168: aspect_ratio на главном экране (точная версия)")
    print("=" * 76)
    print()

    print("--- MonitorPage.jsx ---")
    b = monitor_jsx.with_suffix(".jsx.bak-168")
    b.write_text(monitor_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    content = monitor_jsx.read_text(encoding="utf-8")

    if "PATCH-168" in content:
        print("  [OK] Уже применён")
        return

    m = 0

    # 1. gridTemplateColumns: 1fr -> minmax(0,1fr)
    old = "    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, 1fr)`"
    new = "    gridStyle.gridTemplateColumns = `repeat(${setData.max_columns}, minmax(0, 1fr))`  // PATCH-168"
    if old in content:
        content = content.replace(old, new, 1); m += 1
        print("  [OK] колонки minmax(0,1fr)")

    # 2. Удаляем блок gridTemplateRows
    old = """  if (setData && setData.max_rows > 0) {
    gridStyle.gridTemplateRows = `repeat(${setData.max_rows}, 1fr)`
  }
"""
    if old in content:
        content = content.replace(old, "", 1); m += 1
        print("  [OK] строки auto (удалено)")

    # 3. cellAspect перед hasFixedGrid
    old = "  const hasFixedGrid = setData && setData.max_columns > 0 && setData.max_rows > 0"
    if old in content and "cellAspect" not in content:
        content = content.replace(old,
            "  // PATCH-168: пропорции ячейки из формата набора\n"
            "  const cellAspect = ((setData && setData.aspect_ratio) || '16:9').replace(':', ' / ')\n" + old, 1)
        m += 1
        print("  [OK] cellAspect")

    # 4. CameraCard в .aspect-wrap (ТОЧНЫЙ якорь из файла)
    old = """            return (
              <CameraCard
                key={camera.id}
                camera={camera}
                status={status}
                onContextMenu={handleContextMenu}
                onFullscreen={handleFullscreen}
              />
            )"""
    new = """            return (
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
    else:
        print("  [FAIL] Якорь CameraCard не найден!")

    # 5. CameraEmpty в .aspect-wrap (ТОЧНЫЙ якорь из файла)
    old = """          {Array.from({ length: emptyCount }).map((_, i) => (
            <CameraEmpty key={`empty-${i}`} index={i} />
          ))}"""
    new = """          {Array.from({ length: emptyCount }).map((_, i) => (
            <div key={`empty-${i}`} className="aspect-wrap" style={{ aspectRatio: cellAspect }}>
              <CameraEmpty index={i} />
            </div>
          ))}"""
    if old in content:
        content = content.replace(old, new, 1); m += 1
        print("  [OK] CameraEmpty в .aspect-wrap")
    else:
        print("  [FAIL] Якорь CameraEmpty не найден!")

    if m == 5 and content.count('{') == content.count('}'):
        monitor_jsx.write_text(content, encoding="utf-8")
        print("  [OK] Сохранено")
    else:
        print(f"  [FAIL] {m}/5 — откат")
        monitor_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # CSS монитора
    print()
    print("--- layout.css / camera.css ---")
    css = layout_css.read_text(encoding="utf-8")
    if "PATCH-168" not in css:
        css += "\n/* PATCH-168: строки auto, скролл внутри */\n.fullscreen-grid { align-content: start; overflow: auto; }\n"
        layout_css.write_text(css, encoding="utf-8")
        print("  [OK] layout.css")

    css = camera_css.read_text(encoding="utf-8")
    if "aspect-wrap" not in css:
        css += """
/* PATCH-168: обёртка ячейки с пропорциями набора */
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
    print("✅ Готово! Оба экрана реагируют на aspect_ratio.")
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()