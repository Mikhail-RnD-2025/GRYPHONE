#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
125v2. update_scripts/125_remove_first_frame_timeout.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Убирает избыточный механизм first_frame, который убивает
  работающий ffmpeg через 15 секунд.

СТРАТЕГИЯ:
  Заменяем ВЕСЬ известный блок целиком (безопаснее, чем
  построчное удаление).

ЗАПУСК: python update_scripts/125_remove_first_frame_timeout.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    worker = project_root / "app" / "workers" / "hls_worker.py"

    print("=" * 76)
    print("125 v2: Удаление избыточного таймаута (замена блока)")
    print("=" * 76)
    print()

    backup = worker.with_suffix(".py.bak-125")
    backup.write_text(worker.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = worker.read_text(encoding="utf-8")

    if "PATCH-125v2" in content:
        print("  [OK] Патч 125v2 уже применён")
        return

    changes = []

    # ================================================================
    # ИЗМЕНЕНИЕ 1: убрать first_frame = asyncio.Event()
    # ================================================================
    # Ищем строку с first_frame = asyncio.Event() и удаляем её
    lines = content.split("\n")
    new_lines = []
    for line in lines:
        if "first_frame = asyncio.Event()" in line:
            changes.append(f"Удалена: {line.strip()}")
            continue
        new_lines.append(line)
    content = "\n".join(new_lines)

    # ================================================================
    # ИЗМЕНЕНИЕ 2: убрать first_frame.set()
    # ================================================================
    lines = content.split("\n")
    new_lines = []
    for line in lines:
        if "first_frame.set()" in line:
            changes.append(f"Удалена: {line.strip()}")
            continue
        new_lines.append(line)
    content = "\n".join(new_lines)

    # ================================================================
    # ИЗМЕНЕНИЕ 3: заменить блок таймаута на простой await
    # Ищем от "connect_timeout = global_cfg.get" до последней строки
    # с _t.cancel() и заменяем на "return_code = await proc.wait()"
    # ================================================================
    lines = content.split("\n")
    start_idx = None
    end_idx = None

    # Ищем начало блока таймаута
    for i, line in enumerate(lines):
        if "connect_timeout = global_cfg.get" in line:
            start_idx = i
            break

    if start_idx is None:
        print("  [WARN] Блок таймаута не найден — возможно, уже убран")
    else:
        # Определяем отступ начала блока
        base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())

        # Ищем конец блока (строка с тем же отступом, что и начало,
        # но не пустая и не комментарий)
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if line.strip() == "":
                continue
            cur_indent = len(line) - len(line.lstrip())
            # Если отступ меньше или равен базовому — это конец блока
            # Но нужно проверить, что это НЕ строка, продолжающая блок
            if cur_indent <= base_indent:
                end_idx = i
                break
            # Специальный случай: строка `for _t in (_wf, _we):` и её тело
            # считаем частью блока
            if "for _t in (_wf, _we):" in line:
                continue
            if "_t.cancel()" in line:
                continue
            if "if not _t.done():" in line:
                continue

        # Если нашли начало, но не нашли конец — ищем по другому признаку
        if end_idx is None:
            # Ищем последнюю строку с _t.cancel() после start_idx
            for i in range(len(lines) - 1, start_idx, -1):
                if "_t.cancel()" in lines[i]:
                    end_idx = i + 1  # включаем следующую строку тоже
                    break

        if end_idx is not None and start_idx is not None:
            # Получаем отступ
            indent = " " * base_indent

            # Заменяем блок на одну строку
            new_block = [f"{indent}return_code = await proc.wait()  # PATCH-125v2"]

            old_block = lines[start_idx:end_idx]
            lines[start_idx:end_idx] = new_block

            changes.append(f"Заменён блок таймаута ({len(old_block)} строк) "
                          f"на return_code = await proc.wait()")

            content = "\n".join(lines)
        else:
            print(f"  [WARN] Не удалось определить границы блока "
                  f"(start={start_idx}, end={end_idx})")

    # ================================================================
    # ПРОВЕРКА СИНТАКСИСА
    # ================================================================
    print()
    print("--- Применённые изменения ---")
    for c in changes:
        print(f"  • {c}")
    print()

    print("--- Проверка синтаксиса ---")
    try:
        compile(content, str(worker), "exec")
        print("  [OK] Синтаксис корректен")
    except SyntaxError as e:
        print(f"  [FAIL] Ошибка: {e}")
        print(f"  Линия {e.lineno}: {e.text}")
        worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        print("  Файл восстановлен из бэкапа")
        print()
        print("  Пришлите строки 100-200 hls_worker.py:")
        print("    sed -n '100,200p' app/workers/hls_worker.py")
        sys.exit(1)

    # Проверка баланса скобок
    open_braces = content.count("{")
    close_braces = content.count("}")
    open_parens = content.count("(")
    close_parens = content.count(")")

    if open_braces != close_braces:
        print(f"  [FAIL] Фигурные: {open_braces} vs {close_braces}")
        worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    if open_parens != close_parens:
        print(f"  [FAIL] Круглые: {open_parens} vs {close_parens}")
        worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print(f"  [OK] Скобки сбалансированы "
          f"({{}}:{open_braces}, ():{open_parens})")

    worker.write_text(content, encoding="utf-8")
    print("  [OK] Файл сохранён")
    print()

    print("=" * 76)
    print("✅ Готово! Таймаут первого кадра убран.")
    print()
    print("Что теперь:")
    print("  • ffmpeg работает, пока не завершится сам")
    print("  • HLS сегменты создаются стабильно")
    print("  • Видео в сетке НЕ пропадает через 15 сек")
    print("  • Статус 'в_сети' устанавливается через ffprobe (PATCH-124)")
    print()
    print("Перезапустите сервер:")
    print("  python main.py")
    print()
    print("В логах НЕ должно быть:")
    print("  ⏱ ... нет кадров за 15 с — таймаут")
    print()
    print("Должно быть:")
    print("  ✅ ...: поток доступен (codec=h264)")
    print("  ✅ ...: режим=copy (кодек=h264)")
    print("  [и ffmpeg продолжает работать]")
    print("=" * 76)


if __name__ == "__main__":
    main()