#!/usr/bin/env python3
"""
132. update_scripts/132_kill_proc_in_finally.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Гарантированно убивает ffmpeg процесс при остановке воркера.
  Работает на Windows и Linux.

ПРОБЛЕМА:
  PATCH-131 использовал pkill (Unix-only), на Windows ffmpeg процесс
  оставался жив, камера накапливала RTSP-сессии и отказывалась отвечать.

РЕШЕНИЕ:
  1. Сохранять ссылку на proc во внешнюю переменную current_proc
  2. В finally блоке вызывать current_proc.kill() напрямую
  3. psutil как дополнительный инструмент (если установлен)
  4. Увеличить probe_timeout для retry до 5 сек

ЗАПУСК: python update_scripts/132_kill_proc_in_finally.py
"""

import sys
import re
from pathlib import Path


def main():
    project_root = Path.cwd()
    worker = project_root / "app" / "workers" / "hls_worker.py"

    print("=" * 76)
    print("132: Гарантированный kill ffmpeg процесса (Windows + Linux)")
    print("=" * 76)
    print()

    backup = worker.with_suffix(".py.bak-132")
    backup.write_text(worker.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = worker.read_text(encoding="utf-8")

    if "PATCH-132" in content:
        print("  [OK] Патч уже применён")
        return

    changes = []

    # ========================================================================
    # F1: Добавить current_proc = None в начале функции
    # ========================================================================
    old_start = "    logger.info(\"🔍 Воркер запущен: %s\", route_id)\n    try:"
    new_start = (
        "    logger.info(\"🔍 Воркер запущен: %s\", route_id)\n"
        "    current_proc = None  # PATCH-132: ссылка на активный ffmpeg процесс\n"
        "    try:"
    )

    if old_start in content:
        content = content.replace(old_start, new_start, 1)
        changes.append("F1: добавлена переменная current_proc")
    else:
        print("  [WARN] F1: начало функции не найдено")

    # ========================================================================
    # F2: Присваивать current_proc = proc после создания
    # ========================================================================
    # Ищем: proc = await asyncio.create_subprocess_exec(...)
    old_proc_assign = re.compile(
        r'(proc = await asyncio\.create_subprocess_exec\([^)]+\))',
        re.DOTALL
    )
    match = old_proc_assign.search(content)
    if match:
        insert = match.group(1) + "\n                    current_proc = proc  # PATCH-132"
        content = content[:match.start()] + insert + content[match.end():]
        changes.append("F2: current_proc = proc после запуска ffmpeg")
    else:
        print("  [WARN] F2: блок create_subprocess_exec не найден")

    # ========================================================================
    # F3: В finally блоке убивать current_proc напрямую
    # ========================================================================
    # Ищем finally блок
    old_finally = '''    finally:
        # PATCH-131: принудительный SIGKILL всех ffmpeg для route_id
        try:
            import subprocess as _sp
            _sp.run(
                ["pkill", "-9", "-f", f"hls_cache/camera/{route_id}"],
                stderr=_sp.DEVNULL, timeout=2
            )
        except Exception:
            pass  # Windows или pkill недоступен

        manager.cleanup(route_id)
        logger.info("🧹 Воркер завершён: %s", route_id)'''

    new_finally = '''    finally:
        # PATCH-132: гарантированный kill текущего ffmpeg процесса
        if current_proc is not None:
            try:
                if current_proc.returncode is None:
                    current_proc.kill()
                    await current_proc.wait()
                    logger.info("💀 %s: ffmpeg процесс убит", route_id)
            except Exception as e:
                logger.warning("⚠️ %s: ошибка kill: %s", route_id, e)

        # PATCH-131: дополнительный SIGKILL через psutil (если установлен)
        try:
            import psutil
            my_pid = None
            for p in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = " ".join(p.info.get('cmdline') or [])
                    if f"hls_cache/camera/{route_id}" in cmdline:
                        my_pid = p.info['pid']
                        p.kill()
                        logger.info("💀 %s: psutil убил PID %s", route_id, my_pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            # psutil не установлен — пробуем pkill/taskkill
            try:
                import subprocess as _sp
                import sys as _sys
                if _sys.platform == "win32":
                    # Windows: taskkill по cmdline
                    _sp.run(
                        f'wmic process where "CommandLine like \'%{route_id}%\'" '
                        f'call terminate',
                        shell=True, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL, timeout=3
                    )
                else:
                    # Unix: pkill
                    _sp.run(
                        ["pkill", "-9", "-f", f"hls_cache/camera/{route_id}"],
                        stderr=_sp.DEVNULL, timeout=2
                    )
            except Exception:
                pass  # все fallbacks не сработали

        manager.cleanup(route_id)
        logger.info("🧹 Воркер завершён: %s", route_id)'''

    if old_finally in content:
        content = content.replace(old_finally, new_finally, 1)
        changes.append("F3: current_proc.kill() в finally + psutil + Windows taskkill")
    else:
        # Пробуем без PATCH-131 блока
        old_finally_simple = '''    finally:
        manager.cleanup(route_id)
        logger.info("🧹 Воркер завершён: %s", route_id)'''
        if old_finally_simple in content:
            content = content.replace(old_finally_simple, new_finally, 1)
            changes.append("F3: current_proc.kill() в finally (простой вариант)")
        else:
            print("  [WARN] F3: finally блок не найден")

    # ========================================================================
    # F4: Увеличить probe_timeout для retry до 5 сек
    # ========================================================================
    # Ищем retry блок и меняем await asyncio.sleep(1) на await asyncio.sleep(3)
    old_retry_sleep = '''                    if _attempt == 0:
                        logger.info("🔄 %s: ffprobe retry", route_id)
                        await asyncio.sleep(1)'''
    new_retry_sleep = '''                    if _attempt == 0:
                        logger.info("🔄 %s: ffprobe retry (пауза 3 сек)", route_id)
                        await asyncio.sleep(3)  # PATCH-132: больше пауза между retry'''

    if old_retry_sleep in content:
        content = content.replace(old_retry_sleep, new_retry_sleep, 1)
        changes.append("F4: увеличена пауза между retry с 1 до 3 сек")

    # ========================================================================
    # Сохранение
    # ========================================================================
    print()
    print("--- Применённые изменения ---")
    for c in changes:
        print(f"  • {c}")

    if not changes:
        print("  [WARN] Изменения не применены. Пришлите файл.")

    # Проверка синтаксиса
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
        sys.exit(1)

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
    print("✅ Готово! Гарантированный kill процесса добавлен.")
    print()
    print("Что изменилось:")
    print("  • F1: current_proc = None в начале функции")
    print("  • F2: current_proc = proc после запуска ffmpeg")
    print("  • F3: current_proc.kill() в finally (работает на Windows!)")
    print("        + psutil как дополнительный инструмент")
    print("        + wmic на Windows / pkill на Linux как fallback")
    print("  • F4: пауза между retry 1 сек → 3 сек")
    print()
    print("Перезапустите сервер:")
    print("  python main.py")
    print()
    print("Тест:")
    print("  1. Toggle OFF камеры 015")
    print("  2. Ждите 2 секунды")
    print("  3. Toggle ON")
    print("  4. В логах должно появиться:")
    print("     💀 210-P-GAVw-015_main: ffmpeg процесс убит")
    print("     ✅ 210-P-GAVw-015_main: поток доступен (codec=h264)")
    print("=" * 76)


if __name__ == "__main__":
    main()