#!/usr/bin/env python3
"""
127. update_scripts/127_final_cleanup.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Финальная очистка остатков механизма first_frame из hls_worker.py.

УДАЛЯЕТ:
  • Все строки с _wf, _we, _done, _pending
  • connect_timeout и asyncio.wait с FIRST_COMPLETED
  • Весь блок таймаута (строки 176-207)

ЗАПУСК: python update_scripts/127_final_cleanup.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    worker = project_root / "app" / "workers" / "hls_worker.py"

    print("=" * 76)
    print("127: Финальная очистка остатков механизма таймаута")
    print("=" * 76)
    print()

    backup = worker.with_suffix(".py.bak-127")
    backup.write_text(worker.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = worker.read_text(encoding="utf-8")
    lines = content.split("\n")

    # Паттерны для удаления
    remove_patterns = [
        "_wf",
        "_we",
        "_done",
        "_pending",
        "connect_timeout",
        "ensure_future(proc.wait())",
        "asyncio.wait(",
        "FIRST_COMPLETED",
        "if _we in _done:",
        "elif _wf in _done:",
        "for _t in (_wf, _we):",
        "_t.cancel()",
        "if not _t.done():",
        "return_code = _we.result()",
        "Таймаут подключения",
        "нет кадров за",
        "PATCH-122v4: таймаут подключения",
        "завершение процесса или connect_timeout",
    ]

    new_lines = []
    removed = []

    for i, line in enumerate(lines, 1):
        if any(pattern in line for pattern in remove_patterns):
            removed.append((i, line.strip()))
            continue
        new_lines.append(line)

    content = "\n".join(new_lines)

    print(f"  [OK] Удалено строк: {len(removed)}")
    if removed:
        print("  Удалённые строки:")
        for line_num, line_text in removed[:10]:  # Показываем первые 10
            print(f"    {line_num}: {line_text}")
        if len(removed) > 10:
            print(f"    ... и ещё {len(removed) - 10}")
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

    # Проверка, что мусор удалён
    remaining = []
    for pattern in ["_wf", "_we", "connect_timeout", "FIRST_COMPLETED"]:
        if pattern in content:
            remaining.append(pattern)

    if remaining:
        print(f"  [FAIL] Остался мусор: {remaining}")
        worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print("  [OK] Мусор полностью удалён")

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
    print("✅ Готово! Мусор удалён.")
    print()
    print("Теперь пересоздайте коммит:")
    print("  git add app/workers/hls_worker.py")
    print("  git commit --amend --no-edit")
    print("  git push --force")
    print()
    print("Или создайте новый коммит:")
    print("  git add -A")
    print("  git commit -m 'fix: remove leftover timeout mechanism'")
    print("  git push")
    print("=" * 76)


if __name__ == "__main__":
    main()