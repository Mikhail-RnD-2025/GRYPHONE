#!/usr/bin/env python3
"""
166. update_scripts/166_aspect_ratio_final.py
----------------------------------------------------------------------------
Точная версия PATCH-165 с якорями, взятыми из реального файла SetsPage.jsx
(commit 757d54d). Все 4 замены гарантированно пройдут.

ЗАПУСК: python update_scripts/166_aspect_ratio_final.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    sets_jsx = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"
    sets_css = project_root / "frontend" / "src" / "styles" / "sets.css"

    print("=" * 76)
    print("166: aspect_ratio рендер (финальная версия)")
    print("=" * 76)
    print()

    print("--- SetsPage.jsx ---")
    b = sets_jsx.with_suffix(".jsx.bak-166")
    b.write_text(sets_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    content = sets_jsx.read_text(encoding="utf-8")

    if "PATCH-166" in content:
        print("  [OK] Уже применён")
        return

    n = 0

    # 1. gridTemplateColumns: 1fr -> minmax(0, 1fr)
    old = "                gridTemplateColumns: `repeat(${maxCols}, 1fr)`,"
    new = "                gridTemplateColumns: `repeat(${maxCols}, minmax(0, 1fr))`,  // PATCH-166"
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] колонки minmax(0,1fr)")
    else:
        print("  [WARN] колонки не найдены")

    # 2. Удаляем gridTemplateRows (с последующей закрывающей строкой style)
    old = "                gridTemplateColumns: `repeat(${maxCols}, minmax(0, 1fr))`,  // PATCH-166\n                gridTemplateRows: `repeat(${maxRows}, 1fr)`"
    new = "                gridTemplateColumns: `repeat(${maxCols}, minmax(0, 1fr))`  // PATCH-166"
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] строки auto (удалено)")

    # 3. cellAspect
    old = "  const maxRows = activeSet ? activeSet.max_rows : 1"
    if old in content and "cellAspect" not in content:
        content = content.replace(old,
            old + "\n  // PATCH-166: пропорции ячейки из формата набора\n"
                  "  const cellAspect = ((activeSet && activeSet.aspect_ratio) || '16:9').replace(':', ' / ')", 1)
        n += 1
        print("  [OK] cellAspect")

    # 4. aspectRatio на ячейках — ТОЧНЫЙ якорь из файла
    old = """                    className={'sets-cell' + (cam ? ' has-cam' : '') +
                      (dropTarget === idx ? ' drag-over' : '')}
                    onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}"""
    new = """                    className={'sets-cell' + (cam ? ' has-cam' : '') +
                      (dropTarget === idx ? ' drag-over' : '')}
                    style={{ aspectRatio: cellAspect }}
                    onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}"""
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] aspectRatio на ячейках")
    else:
        print("  [FAIL] Якорь не найден!")
        print("  Показываю фрагмент файла:")
        idx = content.find("'sets-cell'")
        if idx >= 0:
            print("  >>>")
            print(content[idx-50:idx+250])
            print("  <<<")

    if n == 4 and content.count('{') == content.count('}'):
        sets_jsx.write_text(content, encoding="utf-8")
        print("  [OK] Сохранено")
    else:
        print(f"  [FAIL] {n}/4 — откат")
        sets_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # CSS
    print()
    print("--- sets.css ---")
    css = sets_css.read_text(encoding="utf-8")
    if "PATCH-166" not in css:
        css += "\n/* PATCH-166: строки auto не растягиваются */\n.sets-grid { align-content: start; overflow: auto; }\n"
        sets_css.write_text(css, encoding="utf-8")
        print("  [OK] sets.css")

    print()
    print("=" * 76)
    print("✅ Готово! Сетка наборов с aspect_ratio.")
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()