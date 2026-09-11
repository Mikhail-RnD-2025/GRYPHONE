#!/usr/bin/env python3
"""
226.2 update_scripts/226_2_add_warnings_to_return.py
----------------------------------------------------------------------------
Добавляет 'warnings' в return statement import_from_json
(универсальный якорь — находит return { внутри функции).

ЗАПУСК: python update_scripts/226_2_add_warnings_to_return.py
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
    print("226.2: добавление 'warnings' в return import_from_json")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-2262")
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

    # Ищем return { внутри функции
    return_idx = None
    for i in range(json_func_idx, min(json_func_idx + 100, len(lines))):
        if lines[i].strip().startswith("return {"):
            return_idx = i
            break

    if return_idx is None:
        print("  [FAIL] return { не найден")
        sys.exit(1)

    # Ищем закрывающую } (с отступом 12 пробелов — как return)
    close_brace_idx = None
    for i in range(return_idx + 1, min(return_idx + 20, len(lines))):
        if lines[i].strip() == "}":
            close_brace_idx = i
            break

    if close_brace_idx is None:
        print("  [FAIL] закрывающая } не найдена")
        sys.exit(1)

    # Проверяем, есть ли уже 'warnings' в return
    return_block = "\n".join(lines[return_idx:close_brace_idx + 1])
    if "'warnings':" in return_block or '"warnings":' in return_block:
        print("  [OK] 'warnings' уже есть в return")
    else:
        # Вставляем 'warnings': warnings перед закрывающей }
        # Определяем отступ (должен быть как у других полей)
        indent = " " * 16  # 4 пробела от return {
        insert_line = f"{indent}'warnings': warnings,  # PATCH-226.2"
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
    print("✅ PATCH-226.2 готов! Тест:")
    print()
    print(f"  cd {root} && python main.py")
    print()
    print("Откройте /cameras → 📥 Импорт → выберите файл с камерами (*-...)")
    print()
    print("Ожидаемый response:")
    print('  {')
    print('    "success": true,')
    print('    "imported": 24,')
    print('    "updated": 10,')
    print('    "warnings": [')
    print('      {"id": "*-403-P-GAVw-026", "messages": ["ID содержит запрещённые символы: [\'*\']"]}')
    print('    ]')
    print('  }')
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix(import): add warnings to import_from_json return (PATCH-226.2)" \\')
    print('  -m "universal anchor: finds return { inside import_from_json" \\')
    print('  -m "inserts warnings before closing brace" \\')
    print('  -m "API now returns {success, imported, warnings} for UI display"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()