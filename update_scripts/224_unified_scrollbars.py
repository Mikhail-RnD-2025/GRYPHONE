#!/usr/bin/env python3
"""
224. update_scripts/224_unified_scrollbars.py
----------------------------------------------------------------------------
Единый стиль скроллбаров для всего проекта:

  • src/styles.css: глобальный блок (webkit + firefox):
      - тонкий 10px, тёмный track, скруглённый thumb #334155
      - hover-подсветка #475569
      - Firefox: scrollbar-width: thin + scrollbar-color
  • styles/sets.css: удаляем локальные .sets-list::-webkit-scrollbar
    (иначе переопределяют глобальный стиль своим 8px)

Покрывает: /cameras (список+форма), /sets (список+сетка), /status (таблица),
/logs (лента), модалки, dropdown-меню — всё в одном стиле.

ЗАПУСК: python update_scripts/224_unified_scrollbars.py
"""

import re
import sys
from pathlib import Path


def find_project_root():
    p = Path.cwd()
    while True:
        if (p / "frontend").is_dir() and (p / "update_scripts").is_dir():
            return p
        parent = p.parent
        if parent == p:
            print("[FAIL] Не найден корень проекта")
            sys.exit(1)
        p = parent


GLOBAL_SCROLLBAR_CSS = '''

/* ============================================================
   PATCH-224: ЕДИНЫЙ стиль скроллбаров для всего проекта
   ------------------------------------------------------------
   Тёмная тема: track полупрозрачный, thumb #334155, hover #475569.
   Применяется ко всем скроллящимся элементам: списки, таблицы,
   формы, модалки, dropdown-меню.
   ============================================================ */

/* Firefox */
* {
  scrollbar-width: thin;
  scrollbar-color: #334155 rgba(15, 23, 42, 0.4);
}

/* Chrome / Edge / Safari */
::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.4);
  border-radius: 6px;
}
::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 6px;
  border: 2px solid rgba(15, 23, 42, 0.4);
}
::-webkit-scrollbar-thumb:hover {
  background: #475569;
}
::-webkit-scrollbar-thumb:active {
  background: #64748b;
}
::-webkit-scrollbar-corner {
  background: transparent;
}
'''


def main():
    root = find_project_root()
    print("=" * 76)
    print("224: единый стиль скроллбаров для всего проекта")
    print("=" * 76)
    print()

    # 1. Глобальный блок в src/styles.css
    g = root / "frontend" / "src" / "styles.css"
    if not g.exists():
        print("  [FAIL] src/styles.css не найден")
        sys.exit(1)
    b = g.with_suffix(".css.bak-224")
    b.write_text(g.read_text(encoding="utf-8"), encoding="utf-8")
    c = g.read_text(encoding="utf-8")

    if "PATCH-224" in c:
        print("  [OK] styles.css: глобальный блок уже есть")
    else:
        c = c.rstrip() + "\n" + GLOBAL_SCROLLBAR_CSS
        g.write_text(c, encoding="utf-8")
        print("  [OK] styles.css: глобальный блок скроллбаров добавлен")

    # 2. Удаляем локальные scrollbar-правила из sets.css
    s = root / "frontend" / "src" / "styles" / "sets.css"
    b2 = s.with_suffix(".css.bak-224")
    b2.write_text(s.read_text(encoding="utf-8"), encoding="utf-8")
    c2 = s.read_text(encoding="utf-8")

    # Удаляем все блоки .sets-list::-webkit-scrollbar... { ... }
    new_c2, n = re.subn(
        r"\.sets-list::-webkit-scrollbar(?:-thumb|-track)?\s*[^\n{]*(?:\{[^}]*\}|\n)",
        "",
        c2,
    )
    # Страховка: удаляем оставшиеся однострочные правила
    new_c2, n2 = re.subn(
        r"[^\n]*\.sets-list::-webkit-scrollbar[^\n]*\n",
        "",
        new_c2,
    )
    if new_c2 != c2:
        s.write_text(new_c2, encoding="utf-8")
        print(f"  [OK] sets.css: локальные scrollbar-правила удалены ({n + n2})")
    else:
        print("  [SKIP] sets.css: локальных правил не найдено")

    # 3. Проверка: нигде не осталось локальных scrollbar-стилей
    leftover = []
    styles_dir = root / "frontend" / "src" / "styles"
    for f in styles_dir.glob("*.css"):
        txt = f.read_text(encoding="utf-8")
        if "::-webkit-scrollbar" in txt or "scrollbar-width" in txt:
            leftover.append(f.name)
    gtxt = g.read_text(encoding="utf-8")
    if "::-webkit-scrollbar" in gtxt:
        pass  # глобальный — ок
    if leftover:
        print(f"  [WARN] локальные scrollbar-стили остались в: {leftover}")
    else:
        print("  [OK] локальных scrollbar-стилей не осталось — только глобальный")

    print()
    print("=" * 76)
    print("✅ PATCH-224 готов! Сборка + проверка:")
    print()
    print(f"  cd {root}/frontend && npm run build")
    print()
    print("Проверьте (Ctrl+F5) на всех страницах со скроллом:")
    print("  • /cameras — список слева + форма справа")
    print("  • /sets    — список камер + сетка набора")
    print("  • /status  — таблица камер")
    print("  • /logs    — лента логов")
    print()
    print("Ожидаемо везде одинаково:")
    print("  • тонкий скролл 10px")
    print("  • track: полупрозрачный тёмный")
    print("  • thumb: #334155, скруглённый, hover → #475569")
    print("  • Firefox: thin + тёмный thumb")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "style(ui): unified dark scrollbars across all pages (PATCH-224)" \\')
    print('  -m "styles.css: global webkit+firefox scrollbar theme (10px, #334155 thumb)" \\')
    print('  -m "sets.css: removed local .sets-list scrollbar overrides" \\')
    print('  -m "covers: /cameras list+form, /sets list+grid, /status table, /logs feed"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()