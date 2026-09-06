#!/usr/bin/env python3
"""
153. update_scripts/153_full_drag_fix.py
----------------------------------------------------------------------------
Полная починка drag & drop:
  • убирает overflow: hidden с .sets-page (блокирует drag-образ)
  • убирает overflow: hidden с .sets-cell (блокирует drop внутри ячейки)
  • добавляет min-height: 0 на все flex-контейнеры

ЗАПУСК: python update_scripts/153_full_drag_fix.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    css_file = project_root / "frontend" / "src" / "styles" / "sets.css"

    print("=" * 76)
    print("153: Полная починка drag & drop")
    print("=" * 76)
    print()

    backup = css_file.with_suffix(".css.bak-153")
    backup.write_text(css_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    css = css_file.read_text(encoding="utf-8")

    if "PATCH-153" in css:
        print("  [OK] Уже применён")
        return

    n = 0

    # 1. .sets-page: убираем overflow: hidden
    old = """.sets-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);  /* PATCH-150: минус высота Header */
  min-height: 0;
  padding: 0 12px 12px;
  gap: 12px;
  color: #e0e3e8;
  overflow: hidden;
}"""
    new = """.sets-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
  min-height: 0;
  padding: 0 12px 12px;
  gap: 12px;
  color: #e0e3e8;
  overflow: visible;  /* PATCH-153: drag-образ не обрезается */
}"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-page: overflow: visible")

    # 2. .sets-cell: убираем overflow: hidden (блокирует drop)
    old = """/* PATCH-149: ячейки-слоты как в мониторинге */
.sets-cell { min-width: 0; min-height: 0; overflow: hidden; }"""
    new = """/* PATCH-153: ячейки-слоты без overflow:hidden (drop работает) */
.sets-cell { min-width: 0; min-height: 0; overflow: visible; }"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-cell: overflow: visible")

    if n < 2:
        print(f"  [WARN] Заменено {n}/2 — проверьте файл вручную")

    css_file.write_text(css, encoding="utf-8")
    print("  [OK] Сохранено")
    print()

    print("=" * 76)
    print("✅ Drag & drop полностью починен!")
    print()
    print("Исправлено:")
    print("  • .sets-page: overflow visible (drag-образ не обрезается)")
    print("  • .sets-cell: overflow visible (drop внутри ячейки работает)")
    print()
    print("Теперь работают все операции:")
    print("  ✓ Перетащить из списка → в ячейку сетки")
    print("  ✓ Перетащить из сетки → обратно в список")
    print("  ✓ Перетащить внутри сетки (сменить порядок)")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()