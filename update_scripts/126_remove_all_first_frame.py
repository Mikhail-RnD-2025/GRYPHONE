#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
126. update_scripts/126_remove_all_first_frame.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Удаляет ВСЕ строки, содержащие 'first_frame' из hls_worker.py.

ПРИЧИНА:
  После патча 125v2 осталась строка first_frame.set() внутри
  функции _read_logs(), что вызывает NameError.

СТРАТЕГИЯ:
  Простой построчный проход — удаляем любую строку с 'first_frame'.

ЗАПУСК: python update_scripts/126_remove_all_first_frame.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    worker = project_root / "app" / "workers" / "hls_worker.py"

    print("=" * 76)
    print("126: Удаление всех упоминаний first_frame")
    print("=" * 76)
    print()

    backup = worker.with_suffix(".py.bak-126")
    backup.write_text(worker.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = worker.read_text(encoding="utf-8")

    if "PATCH-126" in content:
        print("  [OK] Патч 126 уже применён")
        return

    lines = content.split("\n")
    new_lines = []
    removed = []

    for i, line in enumerate(lines, 1):
        if "first_frame" in line:
            removed.append((i, line.strip()))
            continue
        new_lines.append(line)

    content = "\n".join(new_lines)

    print(f"  [OK] Удалено строк: {len(removed)}")
    for line_num, line_text in removed:
        print(f"    строка {line_num}: {line_text}")
    print()

    # Проверка синтаксиса
    print("--- Проверка синтаксиса ---")
    try:
        compile(content, str(worker), "exec")
        print("  [OK] Синтаксис корректен")
    except SyntaxError as e:
        print(f"  [FAIL] Ошибка: {e}")
        worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        print("  Файл восстановлен из бэкапа")
        sys.exit(1)

    # Проверка, что first_frame больше нигде не упоминается
    if "first_frame" in content:
        print("  [FAIL] first_frame всё ещё упоминается в файле!")
        worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print("  [OK] first_frame полностью удалён")

    # Проверка баланса скобок
    if content.count("{") != content.count("}") or \
       content.count("(") != content.count(")"):
        print("  [FAIL] Скобки не сбалансированы")
        worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print("  [OK] Скобки сбалансированы")

    worker.write_text(content, encoding="utf-8")
    print("  [OK] Файл сохранён")
    print()

    print("=" * 76)
    print("✅ Готово! Все упоминания first_frame удалены.")
    print()
    print("Перезапустите сервер:")
    print("  python main.py")
    print()
    print("В логах НЕ должно быть:")
    print("  name 'first_frame' is not defined")
    print()
    print("Должно быть:")
    print("  ✅ ...: поток доступен (codec=h264)")
    print("  ✅ ...: режим=copy (кодек=h264)")
    print("  [ffmpeg продолжает работать без ошибок]")
    print("=" * 76)


if __name__ == "__main__":
    main()