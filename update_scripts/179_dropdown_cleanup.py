#!/usr/bin/env python3
"""
179. update_scripts/179_dropdown_cleanup.py
----------------------------------------------------------------------------
  • Убирает доп. информацию (размер · формат) из опций dropdown — только имя
  • Ширина выпадающего списка = ширина селектора в шапке (width: 100%)
  • Автопоиск корня проекта (работает из любой директории)

ЗАПУСК: python update_scripts/179_dropdown_cleanup.py
"""

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


def main():
    root = find_project_root()
    print(f"  [OK] Корень проекта: {root}")
    print()
    print("=" * 76)
    print("179: dropdown — только названия, ширина = селектору")
    print("=" * 76)
    print()

    header = root / "frontend" / "src" / "components" / "Header.jsx"
    css_file = root / "frontend" / "src" / "styles" / "header.css"

    # --- Header.jsx: убрать meta-спан ---
    print("--- Header.jsx ---")
    b = header.with_suffix(".jsx.bak-179")
    b.write_text(header.read_text(encoding="utf-8"), encoding="utf-8")
    c = header.read_text(encoding="utf-8")

    if "PATCH-179" in c:
        print("  [OK] Уже применён")
    else:
        old = """                          <span className="set-dropdown-item-name">{s.name}</span>
                          <span className="set-dropdown-item-meta">
                            {s.max_columns || 0}×{s.max_rows || 0} · {s.aspect_ratio || '16:9'}
                          </span>"""
        new = """                          <span className="set-dropdown-item-name">{s.name}</span>  {/* PATCH-179: только имя */}"""
        if old in c:
            c = c.replace(old, new, 1)
            if c.count('{') == c.count('}'):
                header.write_text(c, encoding="utf-8")
                print("  [OK] доп. информация убрана")
            else:
                print("  [FAIL] скобки — откат")
                header.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
                sys.exit(1)
        else:
            print("  [FAIL] якорь не найден — откат")
            header.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

    # --- header.css: ширина меню = ширине селектора ---
    print()
    print("--- header.css ---")
    css = css_file.read_text(encoding="utf-8")
    n = 0

    old = """.set-dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 260px;
  max-width: 400px;"""
    new = """.set-dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  width: 100%;  /* PATCH-179: не шире селектора в шапке */"""
    if old in css:
        css = css.replace(old, new, 1); n += 1
        print("  [OK] ширина меню = ширине селектора")

    old = """.set-dropdown-item-meta { font-size: 0.7rem; color: #64748b; white-space: nowrap; }
"""
    if old in css:
        css = css.replace(old, "", 1); n += 1
        print("  [OK] стиль meta удалён")

    if n >= 1:
        css_file.write_text(css, encoding="utf-8")
        print("  [OK] Сохранено")
    else:
        print("  [WARN] замены не найдены — проверьте header.css")

    print()
    print("=" * 76)
    print("✅ Готово!")
    print("  • В опциях dropdown — только название набора")
    print("  • Выпадающий список точно по ширине кнопки-селектора")
    print()
    print(f"  cd {root}/frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "ui: dropdown shows names only, width matches selector (PATCH-179)"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()