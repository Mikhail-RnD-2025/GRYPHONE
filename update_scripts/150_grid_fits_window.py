#!/usr/bin/env python3
"""
150. update_scripts/150_grid_fits_window.py
----------------------------------------------------------------------------
Гарантия умещения сетки в окне (как в мониторинге):
  • .sets-page: height = calc(100vh - 60px) для Header
  • все flex-контейнеры: min-height: 0 + overflow: hidden
  • .sets-grid: overflow: hidden (не auto) — нет скролла

ЗАПУСК: python update_scripts/150_grid_fits_window.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    css_file = project_root / "frontend" / "src" / "styles" / "sets.css"

    print("=" * 76)
    print("150: Гарантия умещения сетки в окне")
    print("=" * 76)
    print()

    backup = css_file.with_suffix(".css.bak-150")
    backup.write_text(css_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    css = css_file.read_text(encoding="utf-8")

    if "PATCH-150" in css:
        print("  [OK] Уже применён")
        return

    n = 0

    # 1. .sets-page: фиксированная высота с учётом Header (60px)
    old = """.sets-page {
  display: flex;
  flex-direction: column;
  height: auto;
  min-height: calc(100vh - 120px);
  padding: 0 12px 12px;
  gap: 12px;
  color: #e0e3e8;
  overflow: hidden;
}"""
    new = """.sets-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);  /* PATCH-150: минус высота Header */
  min-height: 0;
  padding: 0 12px 12px;
  gap: 12px;
  color: #e0e3e8;
  overflow: hidden;
}"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-page: height = calc(100vh - 60px)")

    # 2. .sets-main: добавить overflow: hidden
    old = """.sets-main {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
}"""
    new = """.sets-main {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
  overflow: hidden;  /* PATCH-150 */
}"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-main: overflow: hidden")

    # 3. .sets-grid-wrap: добавить overflow: hidden
    old = """.sets-grid-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}"""
    new = """.sets-grid-wrap {
  flex: 1;
  min-width: 0;
  min-height: 0;  /* PATCH-150 */
  display: flex;
  flex-direction: column;
  overflow: hidden;  /* PATCH-150 */
}"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-grid-wrap: min-height: 0 + overflow: hidden")

    # 4. .sets-grid: убрать auto, поставить hidden
    old = """.sets-grid {
  display: grid;
  gap: 4px;
  flex: 1;
  min-height: 0;
  padding: 8px;
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
  overflow: auto;
  align-content: start;  /* PATCH-148: строки не растягиваются по высоте */
}

/* PATCH-148: ячейки не раздувают grid по горизонтали */
.sets-cell { min-width: 0; }"""
    new = """.sets-grid {
  display: grid;
  gap: 4px;
  flex: 1;
  min-height: 0;
  padding: 8px;
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
  overflow: hidden;  /* PATCH-150: нет скролла, всё умещается */
}

/* PATCH-149: ячейки-слоты как в мониторинге */
.sets-cell { min-width: 0; min-height: 0; overflow: hidden; }"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-grid: overflow: hidden")
    else:
        # Пробуем без PATCH-148 (если 148 не применялся)
        old2 = """.sets-grid {
  display: grid;
  gap: 4px;
  flex: 1;
  min-height: 0;
  padding: 8px;
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
  overflow: auto;
}"""
        new2 = """.sets-grid {
  display: grid;
  gap: 4px;
  flex: 1;
  min-height: 0;
  padding: 8px;
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
  overflow: hidden;  /* PATCH-150: нет скролла */
}

/* PATCH-149: ячейки-слоты */
.sets-cell { min-width: 0; min-height: 0; overflow: hidden; }"""
        if old2 in css:
            css = css.replace(old2, new2, 1); n += 1
            print("  [OK] .sets-grid: overflow: hidden (вариант 2)")

    # 5. .sets-list-panel: добавить min-height: 0 + overflow: hidden
    old = """.sets-list-panel {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
}"""
    new = """.sets-list-panel {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
  min-height: 0;  /* PATCH-150 */
  overflow: hidden;  /* PATCH-150 */
}"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-list-panel: min-height: 0 + overflow: hidden")

    if n < 5:
        print(f"  [WARN] Заменено {n}/5 (некоторые правила могли отсутствовать)")

    css_file.write_text(css, encoding="utf-8")
    print("  [OK] Сохранено")
    print()

    print("=" * 76)
    print("✅ Готово!")
    print()
    print("Теперь:")
    print("  • .sets-page: height = calc(100vh - 60px)")
    print("  • все flex-контейнеры: min-height: 0 + overflow: hidden")
    print("  • .sets-grid: overflow: hidden (нет скролла)")
    print("  • 8×7 слотов заполняют панель — всё умещается в окно")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()