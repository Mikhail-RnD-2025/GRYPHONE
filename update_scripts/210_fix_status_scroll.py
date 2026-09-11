#!/usr/bin/env python3
"""
210.1 update_scripts/210_fix_status_scroll.py
----------------------------------------------------------------------------
StatusPage.jsx: убираем inline height:'auto', который ломал flex-скролл
.tab-content. Скролл возвращается внутрь .tab-content (CSS flex:1 + overflow).

ЗАПУСК: python update_scripts/210_fix_status_scroll.py
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
    f = root / "frontend" / "src" / "pages" / "StatusPage.jsx"

    print("=" * 76)
    print("210.1: фикс скролла /status")
    print("=" * 76)
    print()

    b = f.with_suffix(".jsx.bak-2101")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    old = '<div className="page" style={{ overflowY: \'auto\', height: \'auto\', minHeight: \'100vh\' }}>'
    new = '<div className="page">'

    if old in c:
        c = c.replace(old, new, 1)
        f.write_text(c, encoding="utf-8")
        print("  [OK] inline height:'auto' убран — скролл вернётся в .tab-content")
    elif '<div className="page">' in c:
        print("  [OK] уже исправлено")
    else:
        print("  [FAIL] якорь не найден — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Пересоберите и проверьте:")
    print()
    print(f"  cd {root}/frontend && npm run build")
    print()
    print("  Откройте http://127.0.0.1:5000/status и нажмите Ctrl+F5")
    print("  Прокрутите вниз: Проблемные камеры → 🏥 Здоровье камер")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix(status): restore page scroll for health section (PATCH-210.1)" \\')
    print('  -m "StatusPage: remove inline height:auto breaking .tab-content flex scroll" \\')
    print('  -m "scroll now lives inside .tab-content (CSS flex:1 + overflow-y:auto)"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()