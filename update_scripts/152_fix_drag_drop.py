#!/usr/bin/env python3
"""
152. update_scripts/152_fix_drag_drop.py
----------------------------------------------------------------------------
Фикс drag & drop: убирает overflow: hidden с контейнеров между которыми
происходит перетаскивание. HTML5 drag API не работает через overflow:hidden.

Правильная схема:
  .sets-page      → overflow: hidden (ограничивает всю страницу)
  .sets-main      → overflow: visible  (drag свободно пересекает)
  .sets-grid-wrap → overflow: visible  (drag свободно пересекает)
  .sets-list-panel→ overflow: visible  (drag свободно пересекает)
  .sets-list      → overflow: auto    (скролл только у списка камер)
  .sets-grid      → overflow: auto    (скролл только у сетки если нужно)

ЗАПУСК: python update_scripts/152_fix_drag_drop.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    css_file = project_root / "frontend" / "src" / "styles" / "sets.css"

    print("=" * 76)
    print("152: Фикс drag & drop (overflow: hidden → visible)")
    print("=" * 76)
    print()

    backup = css_file.with_suffix(".css.bak-152")
    backup.write_text(css_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    css = css_file.read_text(encoding="utf-8")

    if "PATCH-152" in css:
        print("  [OK] Уже применён")
        return

    n = 0

    # 1. .sets-main: overflow hidden → visible
    old = """.sets-main {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
  overflow: hidden;  /* PATCH-150 */
}"""
    new = """.sets-main {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
  overflow: visible;  /* PATCH-152: drag пересекает границы */
}"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-main: overflow: visible")

    # 2. .sets-grid-wrap: overflow hidden → visible
    old = """.sets-grid-wrap {
  flex: 1;
  min-width: 0;
  min-height: 0;  /* PATCH-150 */
  display: flex;
  flex-direction: column;
  overflow: hidden;  /* PATCH-150 */
}"""
    new = """.sets-grid-wrap {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: visible;  /* PATCH-152: drag пересекает границы */
}"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-grid-wrap: overflow: visible")

    # 3. .sets-list-panel: overflow hidden → visible
    old = """.sets-list-panel {
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
    new = """.sets-list-panel {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
  min-height: 0;
  overflow: visible;  /* PATCH-152: drag пересекает границы */
}"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-list-panel: overflow: visible")

    # 4. .sets-grid: overflow hidden → auto (скролл при необходимости)
    old = """.sets-grid {
  display: grid;
  gap: 4px;
  flex: 1;
  min-height: 0;
  padding: 8px;
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
  overflow: hidden;  /* PATCH-150: нет скролла */
}"""
    new = """.sets-grid {
  display: grid;
  gap: 4px;
  flex: 1;
  min-height: 0;
  padding: 8px;
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(51, 65, 85, 0.4);
  border-radius: 8px;
  overflow: auto;  /* PATCH-152: скролл при необходимости */
}"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-grid: overflow: auto")

    if n < 4:
        print(f"  [WARN] Заменено {n}/4 — проверьте файл вручную")

    css_file.write_text(css, encoding="utf-8")
    print("  [OK] Сохранено")
    print()

    print("=" * 76)
    print("✅ Drag & drop восстановлен!")
    print()
    print("Схема:")
    print("  .sets-page      → overflow: hidden (страница)")
    print("  .sets-main      → overflow: visible ✓ drag")
    print("  .sets-list-panel→ overflow: visible ✓ drag")
    print("  .sets-grid-wrap → overflow: visible ✓ drag")
    print("  .sets-grid      → overflow: auto   (скролл внутри сетки)")
    print("  .sets-list      → overflow: auto   (скролл списка)")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()
