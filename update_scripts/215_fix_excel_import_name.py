#!/usr/bin/env python3
"""
215. update_scripts/215_fix_excel_import_name.py
----------------------------------------------------------------------------
excel_import.py: добавляет отсутствующий импорт
    from app.services.camera_import_service import camera_import_service
(NameError на /api/cameras/import-excel).

ЗАПУСК: python update_scripts/215_fix_excel_import_name.py
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
    f = root / "app" / "routes" / "excel_import.py"

    print("=" * 76)
    print("215: фикс NameError в excel_import.py")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-215")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "from app.services.camera_import_service import" in c:
        print("  [OK] импорт уже есть")
    else:
        lines = c.split("\n")
        # последний top-level импорт
        last_imp = -1
        for i, ln in enumerate(lines):
            if (ln.startswith("import ") or ln.startswith("from ")) and not ln.startswith(" "):
                last_imp = i
        if last_imp == -1:
            print("  [FAIL] не найдена строка импорта — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)
        lines.insert(
            last_imp + 1,
            "from app.services.camera_import_service import camera_import_service  # PATCH-215",
        )
        c = "\n".join(lines)
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print(f"  [OK] импорт добавлен после строки {last_imp + 1}")
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

    # показать шапку файла для прозрачности
    print()
    print("--- шапка excel_import.py ---")
    for i, ln in enumerate(f.read_text(encoding="utf-8").split("\n")[:20], 1):
        print(f"  {i:3}: {ln}")

    print()
    print("=" * 76)
    print("✅ Готово! Перезапустите сервер и повторите импорт:")
    print()
    print(f"  cd {root} && python main.py")
    print()
    print("  Затем в UI: /cameras → 📥 Импорт из Excel → выберите cameras.xlsx")
    print("  Или curl:")
    print('    curl -s -F "file=@cameras.xlsx" http://127.0.0.1:5000/api/cameras/import-excel')
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix(routes): restore camera_import_service import in excel_import (PATCH-215)" \\')
    print('  -m "NameError on POST /api/cameras/import-excel: name was never imported" \\')
    print('  -m "added module-level import from app.services.camera_import_service"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()