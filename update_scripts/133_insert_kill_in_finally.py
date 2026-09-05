#!/usr/bin/env python3
"""
133v3. update_scripts/133_insert_kill_in_finally.py
Точная вставка на основе найденной структуры finally блока.
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    worker = project_root / "app" / "workers" / "hls_worker.py"

    print("=" * 76)
    print("133 v3: Точная вставка kill по структуре finally")
    print("=" * 76)
    print()

    backup = worker.with_suffix(".py.bak-133")
    backup.write_text(worker.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = worker.read_text(encoding="utf-8")

    if "PATCH-133" in content:
        print("  [OK] Патч уже применён")
        return

    # Проверяем prerequisites
    if "current_proc = None" not in content:
        print("  [ERROR] current_proc не определён (PATCh 132 не сработал)")
        sys.exit(1)
    if "current_proc = proc" not in content:
        print("  [ERROR] current_proc не присваивается")
        sys.exit(1)
    print("  [OK] current_proc готов (PATCh 132 F1+F2)")

    # ========================================================================
    # Ищем точный маркер: finally блок с PATCH-131 SIGKILL
    # ========================================================================
    # Структура из вывода пользователя:
    #     finally:
    #         # ИСПРАВЛЕНО (v33): cleanup не удаляет статус, а сохраняет
    #         # его как «недоступна» (см. обновлённый stream_manager.py).
    #         # PATCH-131: принудительный SIGKILL всех ffmpeg для route_id
    #         try:
    #             import subprocess as _sp
    #             _sp.run(
    #                 ["pkill", "-9", "-f", f"hls_cache/camera/{route_id}"],
    #                 stderr=_sp.DEVNULL, timeout=2
    #             )
    #         except Exception:
    #             pass  # Windows или pkill недоступен
    #
    #         manager.cleanup(route_id)
    #         logger.info("🧹 Воркер завершён: %s", route_id)

    # Пробуем точное совпадение
    old_finally = '''    finally:
        # ИСПРАВЛЕНО (v33): cleanup не удаляет статус, а сохраняет
        # его как «недоступна» (см. обновлённый stream_manager.py).
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
        # PATCH-133: гарантированный kill текущего ffmpeg процесса
        if current_proc is not None:
            try:
                if current_proc.returncode is None:
                    current_proc.kill()
                    try:
                        await current_proc.wait()
                    except Exception:
                        pass
                    logger.info("💀 %s: ffmpeg процесс убит", route_id)
            except Exception as e:
                logger.warning("⚠️ %s: ошибка kill: %s", route_id, e)

        # PATCH-133: дополнительная очистка через psutil / wmic / pkill
        try:
            import psutil
            for p in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = " ".join(p.info.get('cmdline') or [])
                    if f"hls_cache/camera/{route_id}" in cmdline:
                        p.kill()
                        logger.info("💀 %s: psutil убил PID %s", route_id, p.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            try:
                import subprocess as _sp
                import sys as _sys
                if _sys.platform == "win32":
                    # Windows: wmic для kill по cmdline
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
        print("  [OK] Точное совпадение finally блока найдено")
        print("  [OK] Заменён на PATCH-133")
    else:
        # Пробуем найти по ключевой фразе "PATCH-131: принудительный SIGKILL"
        if "PATCH-131: принудительный SIGKILL" in content:
            # Находим finally: перед этой строкой
            idx = content.find("PATCH-131: принудительный SIGKILL")
            # Ищем finally: назад от этой позиции
            finally_idx = content.rfind("    finally:", 0, idx)
            if finally_idx != -1:
                # Находим конец блока (manager.cleanup(route_id))
                cleanup_idx = content.find("manager.cleanup(route_id)", idx)
                if cleanup_idx != -1:
                    # Находим конец строки cleanup и следующий логгер
                    end_idx = content.find("\n", cleanup_idx)
                    end_idx = content.find("\n", end_idx + 1)  # следующая строка (logger)
                    end_idx = content.find("\n", end_idx + 1)  # конец logger

                    # Вычисляем отступ
                    line_start = content.rfind("\n", 0, finally_idx) + 1
                    indent = content[line_start:finally_idx]

                    # Собираем новый finally блок
                    new_block = f'''{indent}finally:
        # PATCH-133: гарантированный kill текущего ffmpeg процесса
        if current_proc is not None:
            try:
                if current_proc.returncode is None:
                    current_proc.kill()
                    try:
                        await current_proc.wait()
                    except Exception:
                        pass
                    logger.info("💀 %s: ffmpeg процесс убит", route_id)
            except Exception as e:
                logger.warning("⚠️ %s: ошибка kill: %s", route_id, e)

        # PATCH-133: дополнительная очистка через psutil / wmic / pkill
        try:
            import psutil
            for p in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = " ".join(p.info.get('cmdline') or [])
                    if f"hls_cache/camera/{route_id}" in cmdline:
                        p.kill()
                        logger.info("💀 %s: psutil убил PID %s", route_id, p.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            try:
                import subprocess as _sp
                import sys as _sys
                if _sys.platform == "win32":
                    _sp.run(
                        f'wmic process where "CommandLine like \'%{route_id}%\'" '
                        f'call terminate',
                        shell=True, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL, timeout=3
                    )
                else:
                    _sp.run(
                        ["pkill", "-9", "-f", f"hls_cache/camera/{route_id}"],
                        stderr=_sp.DEVNULL, timeout=2
                    )
            except Exception:
                pass

        manager.cleanup(route_id)
        logger.info("🧹 Воркер завершён: %s", route_id)'''

                    content = content[:finally_idx] + new_block + content[end_idx:]
                    print("  [OK] finally блок найден по PATCH-131")
                    print("  [OK] Заменён на PATCH-133")
                else:
                    print("  [FAIL] manager.cleanup не найден")
                    sys.exit(1)
            else:
                print("  [FAIL] finally: не найден перед PATCH-131")
                sys.exit(1)
        else:
            print("  [FAIL] Не найден маркер для поиска")
            print("  Пришлите: grep -n 'finally\\|PATCH-131' app/workers/hls_worker.py")
            sys.exit(1)

    # ========================================================================
    # Проверка синтаксиса
    # ========================================================================
    print()
    print("--- Проверка синтаксиса ---")
    try:
        compile(content, str(worker), "exec")
        print("  [OK] Синтаксис корректен")
    except SyntaxError as e:
        print(f"  [FAIL] Ошибка: {e}")
        print(f"  Линия {e.lineno}: {e.text}")
        worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # Финальные проверки
    if "current_proc.kill()" not in content:
        print("  [FAIL] current_proc.kill() не добавлен")
        worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)
    print("  [OK] current_proc.kill() присутствует")

    if "PATCH-133" not in content:
        print("  [FAIL] маркер PATCH-133 отсутствует")
        worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)
    print("  [OK] маркер PATCH-133 на месте")

    worker.write_text(content, encoding="utf-8")
    print("  [OK] Файл сохранён")
    print()

    print("=" * 76)
    print("✅ Готово! Kill процесса в finally блоке добавлен.")
    print()
    print("Что теперь работает:")
    print("  • current_proc.kill() при остановке (Windows + Linux)")
    print("  • psutil для убийства всех ffmpeg для route_id")
    print("  • wmic (Windows) / pkill (Linux) как fallback")
    print("  • Старый PATCH-131 (pkill-only) ЗАМЕНЁН на PATCH-133")
    print()
    print("Перезапустите сервер:")
    print("  python main.py")
    print()
    print("Тест быстрого toggle:")
    print("  1. Toggle OFF")
    print("  2. Toggle ON (сразу)")
    print("  3. В логах: 💀 ffmpeg процесс убит → ✅ поток доступен")
    print("=" * 76)


if __name__ == "__main__":
    main()