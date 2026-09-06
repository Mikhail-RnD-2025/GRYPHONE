#!/usr/bin/env python3
"""
175. update_scripts/175_counter_badge.py
----------------------------------------------------------------------------
Счётчик камер убран из верхней панели (она растягивалась) и сделан
плавающим бейджем в правом верхнем углу сетки.

ЗАПУСК: python update_scripts/175_counter_badge.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    sets_jsx = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"
    sets_css = project_root / "frontend" / "src" / "styles" / "sets.css"

    print("=" * 76)
    print("175: Счётчик камер — плавающий бейдж на сетке")
    print("=" * 76)
    print()

    print("--- SetsPage.jsx ---")
    b = sets_jsx.with_suffix(".jsx.bak-175")
    b.write_text(sets_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    c = sets_jsx.read_text(encoding="utf-8")

    if "PATCH-175" in c:
        print("  [OK] Уже применён")
        return

    n = 0

    # 1. Убираем счётчик из topbar
    old = """          <span className="sets-counter">
            Камер в наборе: {gridCameras.length} / {maxCols * maxRows}
          </span>
"""
    if old in c:
        c = c.replace(old, "", 1); n += 1
        print("  [OK] счётчик убран из topbar")

    # 2. Бейдж в grid-wrap
    old = """          <div className="sets-grid-wrap">
            <div
              ref={gridRef}"""
    new = """          <div className="sets-grid-wrap">
            <div className="sets-grid-badge">
              Камер: {gridCameras.length} / {maxCols * maxRows}
            </div>
            <div
              ref={gridRef}"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] бейдж добавлен")

    if n == 2 and c.count('{') == c.count('}'):
        sets_jsx.write_text(c, encoding="utf-8")
        print("  [OK] Сохранено")
    else:
        print(f"  [FAIL] {n}/2 — откат")
        sets_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # 3. CSS бейджа
    print()
    print("--- sets.css ---")
    css = sets_css.read_text(encoding="utf-8")
    if "PATCH-175" not in css:
        css += """
/* PATCH-175: плавающий бейдж счётчика камер */
.sets-grid-wrap { position: relative; }
.sets-grid-badge {
  position: absolute;
  top: 12px;
  right: 16px;
  z-index: 5;
  padding: 2px 10px;
  font-size: 0.7rem;
  color: #94a3b8;
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 10px;
  backdrop-filter: blur(4px);
  pointer-events: none;
}
"""
        sets_css.write_text(css, encoding="utf-8")
        print("  [OK] стили бейджа")

    print()
    print("=" * 76)
    print("✅ Готово!")
    print("  • topbar — одна строка, кнопки не растягиваются")
    print("  • счётчик — полупрозрачный бейдж в углу сетки")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print("cd /c/GRYPHONE_PROJ/v26")
    print("git add -A")
    print('git commit -m "ui: camera counter as floating badge on grid (PATCH-175)" \\')
    print('  -m "topbar stays single-line; badge shows N / M in grid corner"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()