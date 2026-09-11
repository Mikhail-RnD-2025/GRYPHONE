#!/usr/bin/env python3
"""
226.3 update_scripts/226_3_smart_return_insert.py
----------------------------------------------------------------------------
Добавляет 'warnings' в return import_from_json с авто-запятой:
если предыдущая строка без запятой — добавляет её.

ЗАПУСК: python update_scripts/226_3_smart_return_insert.py
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
    print("226.3: умная вставка 'warnings' с авто-запятой")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-2263")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    lines = f.read_text(encoding="utf-8").split("\n")

    # Находим def import_from_json
    json_func_idx = None
    for i, ln in enumerate(lines):
        if "def import_from_json" in ln:
            json_func_idx = i
            break

    if json_func_idx is None:
        print("  [FAIL] import_from_json не найден")
        sys.exit(1)

    # Ищем МНОГОСТРОЧНЫЙ return { (строка с "return {" и следующая не "}")
    return_idx = None
    for i in range(json_func_idx, min(json_func_idx + 100, len(lines))):
        if lines[i].strip() == "return {":
            return_idx = i
            break

    if return_idx is None:
        print("  [FAIL] многострочный return { не найден")
        sys.exit(1)

    # Ищем закрывающую }
    close_brace_idx = None
    for i in range(return_idx + 1, min(return_idx + 20, len(lines))):
        if lines[i].strip() == "}":
            close_brace_idx = i
            break

    if close_brace_idx is None:
        print("  [FAIL] закрывающая } не найдена")
        sys.exit(1)

    # Проверяем, есть ли уже 'warnings'
    return_block = "\n".join(lines[return_idx:close_brace_idx + 1])
    if "'warnings':" in return_block:
        print("  [OK] 'warnings' уже есть")
    else:
        # Проверяем предыдущую строку (последнее поле)
        prev_line = lines[close_brace_idx - 1]
        prev_stripped = prev_line.rstrip()

        # Если предыдущая строка без запятой — добавляем запятую
        if not prev_stripped.endswith(","):
            lines[close_brace_idx - 1] = prev_stripped + ","
            print(f"  [OK] запятая добавлена в строку {close_brace_idx}")

        # Вставляем 'warnings': warnings перед закрывающей }
        # Отступ = как у полей return (16 пробелов)
        indent = " " * 16
        insert_line = f"{indent}'warnings': warnings,  # PATCH-226.3"
        lines.insert(close_brace_idx, insert_line)
        print(f"  [OK] 'warnings': warnings добавлен в строку {close_brace_idx + 1}")

    c = "\n".join(lines)

    # Sanity check
    try:
        compile(c, str(f), "exec")
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    f.write_text(c, encoding="utf-8")
    print("  [OK] файл сохранён")

    print()
    print("=" * 76)
    print("✅ PATCH-226.3 готов! Тест:")
    print()
    print(f"  cd {root} && python main.py")
    print()
    print("Откройте /cameras → 📥 Импорт → файл с камерами (*-...)")
    print()
    print("Ожидаемый response:")
    print('  {')
    print('    "success": true,')
    print('    "imported": 274,')
    print('    "warnings": [')
    print('      {"id": "*-403-P-GAVw-026", "messages": ["ID содержит запрещённые символы: [\'*\']"]}')
    print('    ]')
    print('  }')
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix(import): smart warnings insert with auto-comma (PATCH-226.3)" \\')
    print('  -m "checks if previous line ends with comma, adds if missing" \\')
    print('  -m "prevents invalid syntax when last field has no trailing comma"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()