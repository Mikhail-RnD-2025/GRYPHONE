#!/usr/bin/env python3
"""
154. update_scripts/154_force_overflow_visible.py
----------------------------------------------------------------------------
Принудительно добавляет overflow: visible ко всем ячейкам и контейнерам
для работы drag & drop.

ЗАПУСК: python update_scripts/154_force_overflow_visible.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    css_file = project_root / "frontend" / "src" / "styles" / "sets.css"

    print("=" * 76)
    print("154: Принудительный фикс overflow: visible")
    print("=" * 76)
    print()

    backup = css_file.with_suffix(".css.bak-154")
    backup.write_text(css_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    css = css_file.read_text(encoding="utf-8")

    if "PATCH-154" in css:
        print("  [OK] Уже применён")
        return

    n = 0

    # 1. .sets-cell: добавить overflow: visible
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
  overflow: visible;  /* PATCH-154: drop работает внутри ячейки */
}"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-cell: overflow: visible")

    # 2. .sets-cell-cam: убрать overflow: hidden
    old = """.sets-cell-cam {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: grab;
  text-align: center;
  min-height: 0;  /* PATCH-150 */
  overflow: hidden;  /* PATCH-150 */
}"""
    new = """.sets-cell-cam {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: grab;
  text-align: center;
  overflow: visible;  /* PATCH-154: drag пересекает границы */
}"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] .sets-cell-cam: overflow: visible")

    # 3. Убедиться что .sets-page имеет overflow: visible
    if "overflow: visible;  /* PATCH-153" not in css:
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
  overflow: visible;  /* PATCH-154: drag-образ не обрезается */
}"""
        if old in css:
            css = css.replace(old, new, 1); n += 1
            print("  [OK] .sets-page: overflow: visible")

    if n == 0:
        print("  [FAIL] Ничего не заменено — проверьте файл вручную")
        print()
        print("Текущее состояние ключевых правил:")
        for line in css.split("\n"):
            if ".sets-page" in line or ".sets-cell" in line or "overflow" in line:
                print(f"  {line}")
        sys.exit(1)

    css_file.write_text(css, encoding="utf-8")
    print("  [OK] Сохранено")
    print()

    print("=" * 76)
    print("✅ Drag & drop должен работать!")
    print()
    print("Проверьте:")
    print("  1. Откройте DevTools (F12) → Elements")
    print("  2. Выберите .sets-cell → Computed → overflow должно быть 'visible'")
    print("  3. Попробуйте перетащить камеру из списка в ячейку")
    print()
    print("Если не работает — пришлите скриншот DevTools с выбранным .sets-cell")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()