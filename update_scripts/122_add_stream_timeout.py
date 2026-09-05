#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
122. update_scripts/122_add_ffmpeg_timeout.py (версия 4, финальная)
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Добавляет таймаут первого кадра ffmpeg-процесса в hls_worker.py.

ИСПРАВЛЕНО в v4:
  • Убран R4 (ломал синтаксис, и он не нужен — probe_camera
    уже имеет таймаут внутри функции probe_timeout)
  • Применяются только R1, R2, R3 — ключевые исправления

ИДЕМПОТЕНТНОСТЬ: маркер PATCH-122v4, повторный запуск безопасен.
ЗАПУСК: python update_scripts/122_add_ffmpeg_timeout.py
============================================================================
"""

import sys
import re
from pathlib import Path


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("122 v4: Таймаут ffmpeg-процесса (финальная версия)")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    worker = project_root / "app" / "workers" / "hls_worker.py"

    # ========================================================================
    # ШАГ 1: Проверка файла
    # ========================================================================
    print("--- ШАГ 1: Проверка hls_worker.py ---")
    if not worker.exists():
        print("  [ERROR] app/workers/hls_worker.py не найден")
        sys.exit(1)

    content = worker.read_text(encoding="utf-8")

    if "PATCH-122v4" in content:
        print("  [OK] Таймаут уже применён (маркер PATCH-122v4)")
        print("=" * 76)
        return

    # Откатываем частичные применения v2/v3
    if "PATCH-122v" in content:
        print("  [INFO] Обнаружена частичная версия — восстанавливаю из бэкапа")
        backup = worker.with_suffix(".py.bak-122")
        if backup.exists():
            worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
            content = worker.read_text(encoding="utf-8")
            print("  [OK] Восстановлено из .bak-122")

    backup = worker.with_suffix(".py.bak-122")
    backup.write_text(content, encoding="utf-8")
    print(f"  [BAK] {backup.name}")
    print()

    # ========================================================================
    # ШАГ 2: Применение изменений (только R1, R2, R3)
    # ========================================================================
    print("--- ШАГ 2: Применение изменений ---")

    # R1: создаём событие первого кадра перед определением _read_logs
    content, n1 = re.subn(
        r'([ \t]*)async def _read_logs\(\):',
        lambda m: (m.group(1) + "first_frame = asyncio.Event()  # PATCH-122v4\n"
                   + m.group(1) + "async def _read_logs():"),
        content, count=1
    )
    print(f"  [{'OK' if n1 else 'WARN'}] R1: событие first_frame создано" if n1
          else "  [WARN] R1: не найдено место для first_frame")

    # R2: устанавливаем событие при первой stats-строке
    content, n2 = re.subn(
        r'(m = _STATS_RE\.search\(text\)\s*\n([ \t]*)if m:)',
        lambda m: (m.group(1) + "\n" + m.group(2)
                   + "    first_frame.set()  # PATCH-122v4"),
        content, count=1
    )
    print(f"  [{'OK' if n2 else 'WARN'}] R2: first_frame.set() при первом кадре" if n2
          else "  [WARN] R2: не найден блок stats")

    # R3: заменяем бесконечный await proc.wait() на ожидание с таймаутом
    def _r3(m):
        indent = m.group(1)
        return f"""{indent}# PATCH-122v4: таймаут подключения — ждём первый кадр,
{indent}# завершение процесса или connect_timeout секунд
{indent}connect_timeout = global_cfg.get("connect_timeout", 15)
{indent}_wf = asyncio.ensure_future(first_frame.wait())
{indent}_we = asyncio.ensure_future(proc.wait())
{indent}_done, _pending = await asyncio.wait(
{indent}    [_wf, _we],
{indent}    timeout=connect_timeout,
{indent}    return_when=asyncio.FIRST_COMPLETED,
{indent})
{indent}if _we in _done:
{indent}    # процесс завершился сам (ошибка или успех)
{indent}    return_code = _we.result()
{indent}elif _wf in _done:
{indent}    # первый кадр получен — поток активен
{indent}    return_code = await proc.wait()
{indent}else:
{indent}    # таймаут: ffmpeg завис без кадров
{indent}    logger.warning("⏱ %s: нет кадров за %s с — таймаут", route_id, connect_timeout)
{indent}    try:
{indent}        proc.kill()
{indent}    except ProcessLookupError:
{indent}        pass
{indent}    return_code = await proc.wait()
{indent}    log_task.cancel()
{indent}    for _t in (_wf, _we):
{indent}        if not _t.done():
{indent}            _t.cancel()
{indent}    manager.set_status(route_id, "недоступна",
{indent}                       f"Таймаут подключения ({{connect_timeout}} с)")
{indent}    backoff = min(backoff * 2, backoff_max)
{indent}    await asyncio.sleep(backoff)
{indent}    continue
{indent}for _t in (_wf, _we):
{indent}    if not _t.done():
{indent}        _t.cancel()
"""

    content, n3 = re.subn(
        r'([ \t]*)return_code = await proc\.wait\(\)',
        _r3, content, count=1
    )
    print(f"  [{'OK' if n3 else 'WARN'}] R3: await proc.wait() заменён на ожидание с таймаутом" if n3
          else "  [WARN] R3: не найден await proc.wait()")
    print()

    if not (n1 and n2 and n3):
        print("  [FAIL] Ключевые замены не применены — файл не изменён")
        print(f"  Восстановите: cp {backup} {worker}")
        sys.exit(1)

    # ========================================================================
    # ШАГ 3: Проверка синтаксиса
    # ========================================================================
    print("--- ШАГ 3: Проверка синтаксиса ---")
    try:
        compile(content, str(worker), "exec")
        print("  [OK] Синтаксис корректен")
    except SyntaxError as e:
        print(f"  [FAIL] Ошибка синтаксиса: {e}")
        print(f"  Восстановите: cp {backup} {worker}")
        sys.exit(1)

    worker.write_text(content, encoding="utf-8")
    print("  [OK] hls_worker.py сохранён")
    print()

    # ========================================================================
    # ИТОГ
    # ========================================================================
    print("=" * 76)
    print("✅ Готово! Таймаут ffmpeg добавлен (v4).")
    print()
    print("Как это работает:")
    print("  1. Воркер запускает ffmpeg и ждёт максимум 15 сек")
    print("  2. Если появился первый кадр → поток активен ('в_сети')")
    print("  3. Если ffmpeg завершился сам → обработка ошибки (как раньше)")
    print("  4. Если за 15 сек нет кадров → kill, статус 'недоступна',")
    print("     backoff и повторная попытка")
    print()
    print("Настройка таймаута (опционально):")
    print("  конфиг → ffmpeg.global.connect_timeout = 20 (секунды)")
    print()
    print("Перезапустите сервер:")
    print("  python main.py")
    print()
    print("В логах сервера ожидайте:")
    print("  ⏱ camera/xxx: нет кадров за 15 с — таймаут")
    print("  → статус 'недоступна' вместо вечного 'подключение'")
    print("=" * 76)


if __name__ == "__main__":
    main()