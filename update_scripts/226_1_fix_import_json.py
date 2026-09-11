#!/usr/bin/env python3
"""
226.1 update_scripts/226_1_fix_import_json.py
----------------------------------------------------------------------------
Точная вставка валидации в import_from_json (без слома try-except).

ЗАПУСК: python update_scripts/226_1_fix_import_json.py
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
    print("226.1: точная вставка в import_from_json")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-2261")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    # 1. Вставляем warnings = [] после errors = [] в import_from_json
    # Якорь: строка с "errors = []" внутри import_from_json (после "added = 0")
    old_json_errors = """            updated = 0
            added = 0
            errors = []"""
    new_json_errors = """            updated = 0
            added = 0
            errors = []
            warnings = []  # PATCH-226"""

    if old_json_errors in c:
        c = c.replace(old_json_errors, new_json_errors, 1)
        print("  [OK] warnings = [] добавлен в import_from_json")
    else:
        print("  [SKIP] warnings уже есть или якорь не найден")

    # 2. Вставляем валидацию перед current_cams[cam_id].update()
    # Якорь: строка с "if cam_id in current_cams:"
    old_merge = """                    if cam_id in current_cams:
                        current_cams[cam_id].update(cam_data)
                        updated += 1
                    else:
                        current_cams[cam_id] = cam_data
                        added += 1"""
    new_merge = """                    # PATCH-226: валидация ID
                    id_warnings = _validate_camera_id(cam_id)
                    if id_warnings:
                        warnings.append({'id': cam_id, 'messages': id_warnings})

                    if cam_id in current_cams:
                        current_cams[cam_id].update(cam_data)
                        updated += 1
                    else:
                        current_cams[cam_id] = cam_data
                        added += 1"""

    if old_merge in c:
        c = c.replace(old_merge, new_merge, 1)
        print("  [OK] валидация вставлена перед merge-логикой")
    else:
        print("  [SKIP] merge-логика уже изменена или якорь не найден")

    # 3. Добавляем 'warnings' в return statement import_from_json
    # Ищем return после import_from_json (строки 410-430)
    # Паттерн: return {'success': True, 'updated': updated, 'added': added, 'errors': errors}
    old_return_json = "return {'success': True, 'updated': updated, 'added': added, 'errors': errors}"
    new_return_json = "return {'success': True, 'updated': updated, 'added': added, 'errors': errors, 'warnings': warnings}  # PATCH-226"

    if old_return_json in c:
        c = c.replace(old_return_json, new_return_json, 1)
        print("  [OK] 'warnings' добавлен в return import_from_json")
    else:
        # Возможно, return многострочный
        old_return_json_multi = """            return {
                'success': True,
                'updated': updated,
                'added': added,
                'errors': errors,
            }"""
        new_return_json_multi = """            return {
                'success': True,
                'updated': updated,
                'added': added,
                'errors': errors,
                'warnings': warnings,  # PATCH-226
            }"""
        if old_return_json_multi in c:
            c = c.replace(old_return_json_multi, new_return_json_multi, 1)
            print("  [OK] 'warnings' добавлен в return (многострочный)")
        else:
            print("  [WARN] return statement не найден — возможно, уже изменён")

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
    print("✅ PATCH-226.1 готов! Тест импорта:")
    print()
    print(f"  cd {root} && python main.py")
    print()
    print("Откройте /cameras → 📥 Импорт из Excel → выберите cameras.xlsx")
    print()
    print("Ожидаемый response:")
    print('  {')
    print('    "success": true,')
    print('    "imported": 24,')
    print('    "warnings": [')
    print('      {"id": "*-403-P-GAVw-026", "messages": ["ID содержит запрещённые символы: [\'*\']"]}')
    print('    ]')
    print('  }')
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix(import): correct warnings insertion in import_from_json (PATCH-226.1)" \\')
    print('  -m "warnings = [] added after errors = [] (not breaking try-except)" \\')
    print('  -m "validation inserted before merge logic (current_cams.update)" \\')
    print('  -m "warnings included in return statement"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()