#!/usr/bin/env python3
"""
128. update_scripts/128_remove_timeout_block.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Удаляет ЦЕЛЫЙ блок таймаута (от # PATCH-122v4 до success = ...),
  сохраняя только:
    • return_code = await proc.wait()  # PATCH-125v2
    • log_task.cancel()

СТРАТЕГИЯ:
  Блочное удаление по границам (надёжнее построчного).

ЗАПУСК: python update_scripts/128_remove_timeout_block.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    worker = project_root / "app" / "workers" / "hls_worker.py"

    print("=" * 76)
    print("128: Точное удаление блока таймаута")
    print("=" * 76)
    print()

    content = worker.read_text(encoding="utf-8")

    # Идемпотентность: если мусора нет — выходим
    if "_wf" not in content and "_we" not in content:
        print("  [OK] Мусор уже удалён, ничего не делаем")
        return

    backup = worker.with_suffix(".py.bak-128")
    backup.write_text(content, encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    lines = content.split("\n")

    # Граница НАЧАЛА: строка с # PATCH-122v4
    start = None
    for i, line in enumerate(lines):
        if "PATCH-122v4" in line:
            start = i
            break

    if start is None:
        print("  [ERROR] Не найдена граница начала (# PATCH-122v4)")
        sys.exit(1)

    # Граница КОНЦА: строка с success = (return_code == 0)
    end = None
    for i in range(start, len(lines)):
        if "success = (return_code == 0)" in lines[i]:
            end = i
            break

    if end is None:
        print("  [ERROR] Не найдена граница конца (success = ...)")
        sys.exit(1)

    print(f"  [OK] Блок найден: строки {start + 1}–{end}")

    base_indent = len(lines[start]) - len(lines[start].lstrip())

    # Из блока сохраняем только 2 ключевые строки (с базовым отступом)
    block = lines[start:end]
    keep = []
    for l in block:
        ind = len(l) - len(l.lstrip())
        if ind == base_indent and (
            "return_code = await proc.wait()" in l
            or l.strip() == "log_task.cancel()"
        ):
            keep.append(l)

    print(f"  [OK] Сохраняем строк: {len(keep)}")
    for l in keep:
        print(f"    • {l.strip()}")

    # Удаляем блок, оставляя keep
    lines[start:end] = keep
    content = "\n".join(lines)

    # Проверка синтаксиса
    print()
    print("--- Проверка синтаксиса ---")
    try:
        compile(content, str(worker), "exec")
        print("  [OK] Синтаксис корректен")
    except SyntaxError as e:
        print(f"  [FAIL] Ошибка: {e}")
        print("  Файл НЕ изменён (бэкап не нужен)")
        sys.exit(1)

    # Проверка, что мусор удалён
    for pattern in ["_wf", "_we", "connect_timeout", "FIRST_COMPLETED"]:
        if pattern in content:
            print(f"  [FAIL] Остался мусор: {pattern}")
            sys.exit(1)
    print("  [OK] Мусор полностью удалён")

    worker.write_text(content, encoding="utf-8")
    print("  [OK] Файл сохранён")
    print()

    print("=" * 76)
    print("✅ Готово! Блок таймаута удалён.")
    print()
    print("Проверьте:")
    print("  grep -n \"_wf\\|_we\\|connect_timeout\" app/workers/hls_worker.py")
    print("  (должно быть ПУСТО)")
    print()
    print("Перезапустите сервер для проверки:")
    print("  python main.py")
    print()
    print("Затем исправьте коммит:")
    print("  git add app/workers/hls_worker.py")
    print("  git commit --amend --no-edit")
    print("  git push --force")
    print("=" * 76)


if __name__ == "__main__":
    main()