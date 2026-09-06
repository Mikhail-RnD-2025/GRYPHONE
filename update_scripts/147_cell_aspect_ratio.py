#!/usr/bin/env python3
"""
147. update_scripts/147_cell_aspect_ratio.py
----------------------------------------------------------------------------
Ячейки сетки соответствуют формату набора (16:9 / 4:3):
  • убираем gridTemplateRows: repeat(N, 1fr) — строки авто
  • каждой ячейке style={{ aspectRatio }} из activeSet.aspect_ratio
  • контейнер .sets-grid уже имеет overflow: auto — скролл при необходимости

ЗАПУСК: python update_scripts/147_cell_aspect_ratio.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    jsx_file = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"

    print("=" * 76)
    print("147: Ячейки сетки с aspect-ratio формата набора")
    print("=" * 76)
    print()

    backup = jsx_file.with_suffix(".jsx.bak-147")
    backup.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = jsx_file.read_text(encoding="utf-8")

    if "PATCH-147" in content:
        print("  [OK] Уже применён")
        return

    n = 0

    # 1. Убираем растягивание строк по высоте
    old = """            style={{
              gridTemplateColumns: `repeat(${maxCols}, 1fr)`,
              gridTemplateRows: `repeat(${maxRows}, 1fr)`
            }}"""
    new = """            style={{
              gridTemplateColumns: `repeat(${maxCols}, 1fr)`
            }}"""
    if old in content:
        content = content.replace(old, new, 1)
        n += 1
        print("  [OK] gridTemplateRows убран (строки авто)")
    else:
        print("  [FAIL] Блок style сетки не найден — откат")
        sys.exit(1)

    # 2. Константа aspect-ratio
    old = """  const maxRows = activeSet ? activeSet.max_rows : 1"""
    new = """  const maxRows = activeSet ? activeSet.max_rows : 1
  // PATCH-147: пропорция ячейки по формату набора
  const cellAspect = ((activeSet && activeSet.aspect_ratio) || '16:9').replace(':', ' / ')"""
    if old in content:
        content = content.replace(old, new, 1)
        n += 1
        print("  [OK] cellAspect вычисляется")

    # 3. style на ячейке
    old = """                <div
                  key={idx}
                  className={'sets-cell' + (cam ? ' has-cam' : '') +
                    (dropTarget === idx ? ' drag-over' : '')}
                  onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}"""
    new = """                <div
                  key={idx}
                  className={'sets-cell' + (cam ? ' has-cam' : '') +
                    (dropTarget === idx ? ' drag-over' : '')}
                  style={{ aspectRatio: cellAspect }}
                  onDragOver={(e) => { handleDragOver(e); setDropTarget(idx) }}"""
    if old in content:
        content = content.replace(old, new, 1)
        n += 1
        print("  [OK] aspectRatio на ячейках")

    if n < 3:
        print(f"  [FAIL] Заменено только {n}/3 — откат")
        jsx_file.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    if content.count('{') != content.count('}') or \
       content.count('(') != content.count(')'):
        print("  [FAIL] Скобки не сбалансированы — откат")
        jsx_file.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    jsx_file.write_text(content, encoding="utf-8")
    print("  [OK] Файл сохранён")
    print()

    print("=" * 76)
    print("✅ Готово!")
    print()
    print("Теперь:")
    print("  • 16:9 → широкие низкие ячейки")
    print("  • 4:3  → более высокие ячейки")
    print("  • Не умещаются → аккуратный скролл внутри .sets-grid")
    print()
    print("  cd frontend && npm run build")
    print("  Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()