#!/usr/bin/env python3
"""
198. update_scripts/198_bool_as_text.py
----------------------------------------------------------------------------
Excel-экспорт: enabled/audio пишутся ТЕКСТОМ 'true'/'false'
(вместо Excel-boolean, который русский Excel показывает как ИСТИНА/ЛОЖЬ).
Импорт продолжает работать: parse_bool понимает и текст, и boolean.

ЗАПУСК: python update_scripts/198_bool_as_text.py
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
    print("198: булевы в Excel как текст true/false")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-198")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    lines = f.read_text(encoding="utf-8").split("\n")
    out = []
    n = 0

    for line in lines:
        s = line.strip()
        ind = line[:len(line) - len(line.lstrip())]

        if s == "bool(cam.enabled), cam.comment, bool(cam.audio), cam.location  # PATCH-197: TRUE/FALSE":
            out.append(ind + "'true' if cam.enabled else 'false',")
            out.append(ind + "cam.comment,")
            out.append(ind + "'true' if cam.audio else 'false',  # PATCH-198: текст, не locale-boolean")
            out.append(ind + "cam.location")
            n += 1
            continue

        out.append(line)

    print(f"  [OK] замен: {n}")

    if n == 1:
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
        print("  [FAIL] якорь не найден — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово!")
    print()
    print("Было (русский Excel):  ИСТИНА / ЛОЖЬ")
    print("Стало (любой Excel):   true / false")
    print()
    print("Импорт понимает оба варианта:")
    print("  • текст 'true'/'false'/'да'/'нет'/'1'/'0'")
    print("  • Excel-boolean (старые файлы)")
    print()
    print("  Перезапустить сервер: python main.py")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix: excel booleans as text true/false, locale-independent (PATCH-198)" \\')
    print('  -m "enabled/audio written as strings; parse_bool accepts text and bool"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()