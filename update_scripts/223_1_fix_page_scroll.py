#!/usr/bin/env python3
"""
223.1 update_scripts/223_1_fix_page_scroll.py
----------------------------------------------------------------------------
Убирает лишний page-level скролл на /cameras:
  • cameras.css: height calc(100vh-60px) → 100% (занимает ровно tab-content)
  • CamerasPage.jsx: tab-content → flex-колонка с overflow hidden
Внутренние скроллы (список слева, форма справа) сохраняются.

ЗАПУСК: python update_scripts/223_1_fix_page_scroll.py
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
    print("=" * 76)
    print("223.1: убираем лишний page-level скролл на /cameras")
    print("=" * 76)
    print()

    # 1. cameras.css: height 100% вместо calc(100vh - 60px)
    css = root / "frontend" / "src" / "styles" / "cameras.css"
    b = css.with_suffix(".css.bak-2231")
    b.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")
    c = css.read_text(encoding="utf-8")

    old_h = "height: calc(100vh - 60px);"
    new_h = "height: 100%;  /* PATCH-223.1: ровно высота tab-content */"
    if old_h in c:
        c = c.replace(old_h, new_h, 1)
        css.write_text(c, encoding="utf-8")
        print("  [OK] cameras.css: height → 100%")
    elif "height: 100%;" in c:
        print("  [OK] cameras.css: уже 100%")
    else:
        print("  [FAIL] якорь height не найден — откат")
        css.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # 2. CamerasPage.jsx: tab-content → flex-колонка, overflow hidden
    pg = root / "frontend" / "src" / "pages" / "CamerasPage.jsx"
    b2 = pg.with_suffix(".jsx.bak-2231")
    b2.write_text(pg.read_text(encoding="utf-8"), encoding="utf-8")
    c2 = pg.read_text(encoding="utf-8")

    old_tab = '<div className="tab-content">'
    new_tab = ('<div className="tab-content" style={{\n'
               '          flex: 1, minHeight: 0, overflow: \'hidden\',\n'
               '          display: \'flex\', flexDirection: \'column\',\n'
               '        }}>  {/* PATCH-223.1 */}')
    if old_tab in c2:
        c2 = c2.replace(old_tab, new_tab, 1)
        pg.write_text(c2, encoding="utf-8")
        print("  [OK] CamerasPage.jsx: tab-content → flex + overflow hidden")
    elif "PATCH-223.1" in c2:
        print("  [OK] CamerasPage.jsx: уже исправлено")
    else:
        print("  [FAIL] якорь tab-content не найден — откат")
        pg.write_text(b2.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Пересоберите:")
    print()
    print(f"  cd {root}/frontend && npm run build")
    print()
    print("Откройте /cameras (Ctrl+F5):")
    print("  • Page-level скролл ИСЧЕЗ (самый правый)")
    print("  • Скролл списка слева — работает")
    print("  • Скролл формы справа — работает")
    print("  • Вся страница умещается в viewport")
    print("=" * 76)
    print()
    print("📦 Коммит (вместе с 223):")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "refactor(cameras): master-detail layout (PATCH-223,223.1)" \\')
    print('  -m "list+inline editor like SetsPage; click to select" \\')
    print('  -m "fix 223.1: remove page-level scroll (height 100% + tab-content flex)" \\')
    print('  -m "inner scrolls preserved: camera list + editor form"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()