#!/usr/bin/env python3
"""
196. update_scripts/196_sub2_alias.py
----------------------------------------------------------------------------
Добавляет алиас 'путь sub2' в COLUMN_MAPPING['sub2_url'],
чтобы файл экспорта импортировался без потерь (round-trip).

ЗАПУСК: python update_scripts/196_sub2_alias.py
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
    f = root / "app" / "services" / "camera_import_service.py"

    print("=" * 76)
    print("196: алиас 'путь sub2' для round-trip импорта")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-196")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "PATCH-196" in c:
        print("  [OK] Уже применён")
        return

    old = """    'sub2_url': [
        'sub2_url', 'sub2 url', 'sub2', 'суб2', 'sub2_path', 'sub2 path',
    ],"""
    new = """    'sub2_url': [
        'sub2_url', 'sub2 url', 'sub2', 'суб2', 'sub2_path', 'sub2 path',
        'путь sub2', 'путь sub2 потока',  # PATCH-196: заголовок экспорта
    ],"""

    if old in c:
        c = c.replace(old, new, 1)
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] алиас добавлен")
        except SyntaxError as e:
            print(f"  [FAIL] {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)
    else:
        print("  [FAIL] якорь не найден — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Перезапустите сервер: python main.py")
    print("=" * 76)
    print()
    print("📦 Коммит (вместе с 195):")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix: Path import in api.py + sub2 alias for round-trip (PATCH-195,196)" \\')
    print('  -m "api.py: from pathlib import Path (export-excel 500 fix)" \\')
    print('  -m "camera_import_service: alias «Путь sub2» matches export header"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()