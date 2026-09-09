#!/usr/bin/env python3
"""
197. update_scripts/197_excel_headers_db_names.py
----------------------------------------------------------------------------
  • Заголовки экспорта Excel = имена колонок БД (английские)
  • Булевы поля пишутся как Excel-boolean (TRUE/FALSE)
  • Round-trip импорт работает (англ. имена есть в COLUMN_MAPPING)

ЗАПУСК: python update_scripts/197_excel_headers_db_names.py
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


NEW_HEADERS = ("headers = ['id', 'name', 'login', 'pass', 'ipaddress', 'port', "
               "'main_url', 'sub_url', 'sub2_url', 'enabled', 'comment', 'audio', "
               "'location']  # PATCH-197: имена колонок БД")


def main():
    root = find_project_root()
    f = root / "app" / "services" / "camera_import_service.py"

    print("=" * 76)
    print("197: заголовки Excel = имена колонок БД + TRUE/FALSE")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-197")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    lines = f.read_text(encoding="utf-8").split("\n")
    out = []
    st = {"headers": 0, "bools": 0}
    i = 0

    while i < len(lines):
        s = lines[i].strip()
        ind = lines[i][:len(lines[i]) - len(lines[i].lstrip())]

        # Заголовок-блок (3 строки) → одна строка с именами БД
        if s == "headers = ['ID', 'Имя', 'Login', 'Пароль', 'IP-адрес', 'Порт',":
            # пропускаем 3 строки старого блока
            i += 3
            out.append(ind + NEW_HEADERS)
            st["headers"] += 1
            continue

        # Булевы в ws.append → явный bool()
        if s == "cam.enabled, cam.comment, cam.audio, cam.location":
            out.append(ind + "bool(cam.enabled), cam.comment, bool(cam.audio), cam.location  # PATCH-197: TRUE/FALSE")
            st["bools"] += 1
            i += 1
            continue

        out.append(lines[i])
        i += 1

    print(f"  [OK] замен: headers={st['headers']} bools={st['bools']}")

    if st["headers"] == 2 and st["bools"] == 1:
        content = "\n".join(out)
        try:
            compile(content, str(f), "exec")
            f.write_text(content, encoding="utf-8")
            print("  [OK] Сохранено")
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)
    else:
        print("  [FAIL] счётчики не сошлись — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Новый вид экспорта:")
    print()
    print("  id | name | login | pass | ipaddress | port | main_url |")
    print("  sub_url | sub2_url | enabled | comment | audio | location")
    print()
    print("  enabled/audio → TRUE / FALSE (Excel-boolean)")
    print()
    print("  Перезапустить сервер: python main.py")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix: excel export headers = DB column names, booleans TRUE/FALSE (PATCH-197)" \\')
    print('  -m "headers: id,name,login,pass,ipaddress,port,main_url,sub_url,sub2_url,enabled,comment,audio,location" \\')
    print('  -m "enabled/audio written as Excel booleans (TRUE/FALSE)" \\')
    print('  -m "round-trip import unaffected (english names in COLUMN_MAPPING)"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()