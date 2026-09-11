#!/usr/bin/env python3
"""
226. update_scripts/226_import_validation.py
----------------------------------------------------------------------------
camera_import_service.py: валидация camera ID при импорте из Excel/JSON.

Проверяет:
  • Запрещённые символы Windows: < > : " / \\ | ? *
  • Пробелы в начале/конце
  • Пустой ID
  • Слишком длинный ID (>200 символов)

Результат:
  • Камеры всё равно импортируются (PATCH-222 санитизирует)
  • warnings возвращаются в API response
  • Пользователь видит проблемные ID ДО того, как они сломают систему

ЗАПУСК: python update_scripts/226_import_validation.py
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


VALIDATION_FUNC = '''
# ============================================================================
# PATCH-226: валидация camera ID (защита от WinError 123)
# Windows запрещает символы: < > : " / \\ | ? *
# ============================================================================
import re as _re_import_val
_INVALID_ID_CHARS = _re_import_val.compile(r'[<>:"/\\\\|?*]')

def _validate_camera_id(cam_id: str) -> list[str]:
    """Возвращает список предупреждений (пусто = валидно)."""
    warnings = []
    if not cam_id:
        warnings.append("ID пустой")
    elif _INVALID_ID_CHARS.search(cam_id):
        found = _INVALID_ID_CHARS.findall(cam_id)
        warnings.append(f"ID содержит запрещённые символы: {found}")
    if cam_id and cam_id != cam_id.strip():
        warnings.append("ID содержит пробелы в начале/конце")
    if cam_id and len(cam_id) > 200:
        warnings.append(f"ID слишком длинный ({len(cam_id)} > 200)")
    return warnings

'''


def main():
    root = find_project_root()
    f = root / "app" / "services" / "camera_import_service.py"

    print("=" * 76)
    print("226: валидация ID при импорте (защита от WinError 123)")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-226")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "PATCH-226" in c:
        print("  [OK] уже применён")
        return

    # 1. Вставляем функцию валидации после helper-функций (строки 103-168)
    # Ищем последнюю helper-функцию (def ... return ...)
    lines = c.split("\n")
    insert_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith("def ") and not lines[i].strip().startswith("def import"):
            # Находим конец этой функции (следующий def или class)
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("def ") or lines[j].strip().startswith("class "):
                    insert_idx = j
                    break
            if insert_idx:
                break

    if insert_idx is None:
        print("  [FAIL] не найдена точка вставки для _validate_camera_id")
        sys.exit(1)

    lines.insert(insert_idx, VALIDATION_FUNC)
    c = "\n".join(lines)
    print(f"  [OK] _validate_camera_id() добавлена в строку {insert_idx}")

    # 2. Интегрируем валидацию в import_from_excel
    # Ищем строку "cameras.append(camera)" и вставляем валидацию перед ней
    lines = c.split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if "cameras.append(camera)" in lines[i]:
            # Вставляем валидацию перед этой строкой
            indent = len(lines[i]) - len(lines[i].lstrip())
            validation_code = [
                " " * indent + "# PATCH-226: валидация ID",
                " " * indent + "id_warnings = _validate_camera_id(camera.get('id', ''))",
                " " * indent + "if id_warnings:",
                " " * indent + "    if 'warnings' not in locals():",
                " " * indent + "        warnings = []",
                " " * indent + "    warnings.append({'id': camera.get('id'), 'messages': id_warnings})",
                "",
            ]
            lines[i:i] = validation_code
            print(f"  [OK] валидация вставлена перед cameras.append() в строке {i}")
            break

    # 3. Инициализируем warnings в начале import_from_excel
    # Ищем "errors = []" и добавляем "warnings = []" после
    for i, ln in enumerate(lines):
        if "errors = []" in ln and "skipped_rows = 0" in lines[i - 1]:
            lines.insert(i + 1, "            warnings = []  # PATCH-226")
            print(f"  [OK] warnings = [] инициализирован в строке {i + 1}")
            break

    # 4. Добавляем warnings в return statement
    # Ищем return {'success': True, 'imported': ...} и добавляем 'warnings'
    for i in range(len(lines) - 1, -1, -1):
        if "'success': True" in lines[i] and "'imported':" in lines[i]:
            # Находим закрывающую скобку
            for j in range(i, min(i + 10, len(lines))):
                if "}" in lines[j]:
                    # Вставляем 'warnings' перед }
                    lines[j] = lines[j].replace("}", "    'warnings': warnings,  # PATCH-226\n        }")
                    print(f"  [OK] 'warnings' добавлен в return в строке {j}")
                    break
            break

    c = "\n".join(lines)

    # 5. Аналогично для import_from_json (строка 372)
    # Ищем "def import_from_json" и добавляем ту же логику
    lines = c.split("\n")
    json_func_idx = None
    for i, ln in enumerate(lines):
        if "def import_from_json" in ln:
            json_func_idx = i
            break

    if json_func_idx:
        # Ищем внутри import_from_json строку "cameras.append(camera)"
        for i in range(json_func_idx, min(json_func_idx + 100, len(lines))):
            if "cameras.append(camera)" in lines[i]:
                indent = len(lines[i]) - len(lines[i].lstrip())
                validation_code = [
                    " " * indent + "# PATCH-226: валидация ID",
                    " " * indent + "id_warnings = _validate_camera_id(camera.get('id', ''))",
                    " " * indent + "if id_warnings:",
                    " " * indent + "    if 'warnings' not in locals():",
                    " " * indent + "        warnings = []",
                    " " * indent + "    warnings.append({'id': camera.get('id'), 'messages': id_warnings})",
                    "",
                ]
                lines[i:i] = validation_code
                print(f"  [OK] валидация вставлена в import_from_json в строке {i}")
                break

        # Ищем "errors = []" внутри import_from_json
        for i in range(json_func_idx, min(json_func_idx + 50, len(lines))):
            if "errors = []" in lines[i] and "warnings" not in lines[i + 1]:
                lines.insert(i + 1, "        warnings = []  # PATCH-226")
                print(f"  [OK] warnings = [] в import_from_json в строке {i + 1}")
                break

        # Добавляем 'warnings' в return
        for i in range(json_func_idx, len(lines)):
            if "'success': True" in lines[i] and "'imported':" in lines[i]:
                for j in range(i, min(i + 10, len(lines))):
                    if "}" in lines[j]:
                        lines[j] = lines[j].replace("}", "    'warnings': warnings,  # PATCH-226\n        }")
                        print(f"  [OK] 'warnings' в return import_from_json в строке {j}")
                        break
                break

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
    print("✅ PATCH-226 готов! Тест импорта:")
    print()
    print(f"  cd {root} && python main.py")
    print()
    print("Откройте /cameras → 📥 Импорт из Excel → выберите cameras.xlsx")
    print()
    print("Ожидаемый response:")
    print('  {')
    print('    "success": true,')
    print('    "imported": 24,')
    print('    "skipped": 0,')
    print('    "errors": [],')
    print('    "warnings": [')
    print('      {"id": "*-403-P-GAVw-026", "messages": ["ID содержит запрещённые символы: [\'*\']"]},')
    print('      {"id": "210-P-GAVw-007 ", "messages": ["ID содержит пробелы в начале/конце"]}')
    print('    ]')
    print('  }')
    print()
    print("Пользователь видит предупреждения и может переименовать камеры в /cameras")
    print("(поиск по * или пробелам).")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat(import): validate camera IDs before import (PATCH-226)" \\')
    print('  -m "camera_import_service: _validate_camera_id() checks for:" \\')
    print('  -m "  - forbidden Windows chars: < > : \" / \\ | ? *" \\')
    print('  -m "  - leading/trailing spaces" \\')
    print('  -m "  - empty ID, too long ID (>200 chars)" \\')
    print('  -m "warnings returned in API response (cameras still imported via PATCH-222)" \\')
    print('  -m "prevents WinError 123 by alerting user before problematic IDs enter DB"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()