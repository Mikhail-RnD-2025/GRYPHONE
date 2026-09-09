#!/usr/bin/env python3
"""
195. update_scripts/195_add_path_import.py
----------------------------------------------------------------------------
Добавляет `from pathlib import Path` в app/routes/api.py

ЗАПУСК: python update_scripts/195_add_path_import.py
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
    f = root / "app" / "routes" / "api.py"

    print("=" * 76)
    print("195: импорт Path в api.py")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-195")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "from pathlib import Path" in c:
        print("  [OK] Path уже импортирован")
        return

    # Вставляем после последнего импорта (перед def register или другим кодом)
    lines = c.split("\n")
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith(("import ", "from ")):
            insert_idx = i + 1
        elif line.strip() and not line.startswith(("#", '"', "'")) and insert_idx > 0:
            break

    lines.insert(insert_idx, "from pathlib import Path  # PATCH-195")
    c = "\n".join(lines)

    try:
        compile(c, str(f), "exec")
        f.write_text(c, encoding="utf-8")
        print("  [OK] `from pathlib import Path` добавлен")
    except SyntaxError as e:
        print(f"  [FAIL] {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Перезапустите сервер:")
    print("  python main.py")
    print()
    print("Затем повторите экспорт Excel — должно скачиваться")
    print("=" * 76)


if __name__ == "__main__":
    main()