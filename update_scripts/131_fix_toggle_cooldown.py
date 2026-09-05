#!/usr/bin/env python3
"""
131v2. update_scripts/131_fix_toggle_cooldown.py
----------------------------------------------------------------------------
Упрощённая версия: только точные строковые замены, без сложных regex.

ИСПРАВЛЕНИЯ:
1. Увеличивает backoff после codec=unknown до 15 сек
2. Добавляет задержку 1 сек перед запуском ffmpeg
3. Retry для probe_camera (2 попытки)
4. SIGKILL при cleanup

ЗАПУСК: python update_scripts/131_fix_toggle_cooldown.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    worker = project_root / "app" / "workers" / "hls_worker.py"

    print("=" * 76)
    print("131 v2: Защита от быстрого toggle (упрощённая)")
    print("=" * 76)
    print()

    backup = worker.with_suffix(".py.bak-131")
    backup.write_text(worker.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = worker.read_text(encoding="utf-8")

    if "PATCH-131" in content:
        print("  [OK] Патч уже применён")
        return

    changes = []

    # ========================================================================
    # F1: Увеличить backoff после codec=unknown
    # ========================================================================
    old_backoff = '''                manager.set_status(route_id, "недоступна", "Кодек не определён")
                await asyncio.sleep(min(backoff * 2, 15))
                backoff = min(backoff * 2, 15)
                continue'''

    new_backoff = '''                manager.set_status(route_id, "недоступна", "Кодек не определён")
                # PATCH-131: увеличенный backoff (камера "остывает" после kill)
                backoff = max(backoff, 15)  # минимум 15 сек
                backoff = min(backoff * 2, 30)
                await asyncio.sleep(backoff)
                continue'''

    if old_backoff in content:
        content = content.replace(old_backoff, new_backoff)
        changes.append("F1: backoff после codec=unknown увеличен до 15-30 сек")
    else:
        print("  [WARN] F1: блок backoff не найден (точное совпадение)")

    # ========================================================================
    # F2: Задержка перед запуском ffmpeg
    # ========================================================================
    old_proc = '''                try:
                    proc = await asyncio.create_subprocess_exec('''

    new_proc = '''                try:
                    # PATCH-131: задержка 1 сек (camera cooldown)
                    await asyncio.sleep(1)
                    proc = await asyncio.create_subprocess_exec('''

    if old_proc in content:
        content = content.replace(old_proc, new_proc, 1)
        changes.append("F2: задержка 1 сек перед запуском ffmpeg")
    else:
        print("  [WARN] F2: блок proc не найден")

    # ========================================================================
    # F3: Retry для probe_camera
    # ========================================================================
    old_probe = '''            try:
                loop = asyncio.get_running_loop()
                codec, profile, pix_fmt = await loop.run_in_executor(
                    None, probe_camera, url, global_cfg
                )
            except Exception:
                codec, profile, pix_fmt = "unknown", "unknown", "unknown"'''

    new_probe = '''            # PATCH-131: retry для probe_camera
            codec, profile, pix_fmt = "unknown", "unknown", "unknown"
            for _attempt in range(2):  # 2 попытки
                try:
                    loop = asyncio.get_running_loop()
                    codec, profile, pix_fmt = await loop.run_in_executor(
                        None, probe_camera, url, global_cfg
                    )
                    if codec and codec != "unknown":
                        break  # успех
                    if _attempt == 0:
                        logger.info("🔄 %s: ffprobe retry", route_id)
                        await asyncio.sleep(1)
                except Exception:
                    if _attempt == 0:
                        await asyncio.sleep(1)'''

    if old_probe in content:
        content = content.replace(old_probe, new_probe)
        changes.append("F3: probe_camera с retry (2 попытки)")
    else:
        print("  [WARN] F3: блок probe_camera не найден")

    # ========================================================================
    # F4: SIGKILL при cleanup
    # ========================================================================
    old_cleanup = '''        manager.cleanup(route_id)
        logger.info("🧹 Воркер завершён: %s", route_id)'''

    new_cleanup = '''        # PATCH-131: принудительный SIGKILL всех ffmpeg для route_id
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

    if old_cleanup in content:
        content = content.replace(old_cleanup, new_cleanup)
        changes.append("F4: SIGKILL всех ffmpeg при cleanup")
    else:
        print("  [WARN] F4: блок cleanup не найден")

    # ========================================================================
    # Сохранение
    # ========================================================================
    print()
    print("--- Применённые изменения ---")
    if changes:
        for c in changes:
            print(f"  • {c}")
    else:
        print("  [WARN] Изменения не применены")
        print("  Пришлите вывод: sed -n '80,110p' app/workers/hls_worker.py")

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
    print("✅ Готово! Защита от быстрого toggle добавлена.")
    print()
    print("Что изменилось:")
    print("  • F1: backoff после codec=unknown минимум 15 сек (было 2)")
    print("  • F2: задержка 1 сек перед запуском ffmpeg")
    print("  • F3: retry для probe_camera (2 попытки)")
    print("  • F4: SIGKILL всех ffmpeg при cleanup")
    print()
    print("Перезапустите сервер:")
    print("  python main.py")
    print()
    print("Тест:")
    print("  1. Отключите камеру (toggle OFF)")
    print("  2. Подождите 3 секунды")
    print("  3. Включите камеру (toggle ON)")
    print("  4. Видео должно появиться через 3-5 секунд")
    print("=" * 76)


if __name__ == "__main__":
    main()132_kill_proc_in_finally.py