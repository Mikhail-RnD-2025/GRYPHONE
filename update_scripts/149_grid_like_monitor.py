#!/usr/bin/env python3
"""
149. update_scripts/149_grid_like_monitor.py
----------------------------------------------------------------------------
Приводит сетку SetsPage к логике главной сетки мониторинга:
  • ячейки-слоты: gridTemplateColumns/Rows = repeat(N, 1fr) — всё умещается
  • убираем aspect-ratio с ячеек (формат держит контент, как object-fit: contain)
  • убираем align-content: start (строки 1fr заполняют контейнер)

ЗАПУСК: python update_scripts/149_grid_like_monitor.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    jsx_file = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"
    css_file = project_root / "frontend" / "src" / "styles" / "sets.css"

    print("=" * 76)
    print("149: Сетка наборов аналогична главной сетке мониторинга")
    print("=" * 76)
    print()

    # --- JSX ---
    print("--- SetsPage.jsx ---")
    backup_jsx = jsx_file.with_suffix(".jsx.bak-149")
    backup_jsx.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_jsx.name}")

    content = jsx_file.read_text(encoding="utf-8")
    if "PATCH-149" in content:
        print("  [OK] Уже применён")
    else:
        n = 0

        # 1. Возвращаем строки 1fr (как в MonitorPage)
        old = """            style={{
              gridTemplateColumns: `repeat(${maxCols}, 1fr)`
            }}"""
        new = """            style={{
              gridTemplateColumns: `repeat(${maxCols}, 1fr)`,
              gridTemplateRows: `repeat(${maxRows}, 1fr)`  // PATCH-149: как в мониторинге
            }}"""
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] gridTemplateRows: repeat(N, 1fr) возвращён")

        # 2. Убираем aspectRatio с ячеек
        old = """                  style={{ aspectRatio: cellAspect }}
"""
        if old in content:
            content = content.replace(old, "", 1); n += 1
            print("  [OK] aspectRatio с ячеек убран")

        # 3. Убираем константу cellAspect
        old = """  // PATCH-147: пропорция ячейки по формату набора
  const cellAspect = ((activeSet && activeSet.aspect_ratio) || '16:9').replace(':', ' / ')
"""
        if old in content:
            content = content.replace(old, "", 1); n += 1
            print("  [OK] константа cellAspect убрана")

        if n < 3:
            print(f"  [FAIL] Заменено {n}/3 — откат")
            jsx_file.write_text(backup_jsx.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        if content.count('{') != content.count('}') or \
           content.count('(') != content.count(')'):
            print("  [FAIL] Скобки — откат")
            jsx_file.write_text(backup_jsx.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        jsx_file.write_text(content, encoding="utf-8")
        print("  [OK] Сохранено")

    # --- CSS ---
    print()
    print("--- sets.css ---")
    css = css_file.read_text(encoding="utf-8")
    m = 0

    # 1. Убираем align-content: start
    old = "  align-content: start;  /* PATCH-148: строки не растягиваются по высоте */\n"
    if old in css:
        css = css.replace(old, "", 1); m += 1
        print("  [OK] align-content: start убран")

    # 2. Ячейка-слот как .camera-card: заполняет слот, не вылезает
    old = """.sets-cell {
  border: 1px solid rgba(51, 65, 85, 0.35);
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  font-size: 0.75rem;
  transition: border-color 0.15s ease, background 0.15s ease;
}"""
    new = """.sets-cell {
  border: 1px solid rgba(51, 65, 85, 0.35);
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  font-size: 0.75rem;
  transition: border-color 0.15s ease, background 0.15s ease;
  /* PATCH-149: ячейка-слот как в главной сетке */
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}"""
    if old in css:
        css = css.replace(old, new, 1); m += 1
        print("  [OK] .sets-cell: min-height/min-width/overflow как слот")

    if m:
        css_file.write_text(css, encoding="utf-8")
        print("  [OK] Сохранено")

    print()
    print("=" * 76)
    print("✅ Готово! Сетка наборов теперь аналог главной сетки:")
    print()
    print("  • 8×7 слотов заполняют панель — всё умещается в окно")
    print("  • нет скролла (как в мониторинге)")
    print("  • формат 16:9/4:3 — свойство набора (для видео, object-fit)")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()