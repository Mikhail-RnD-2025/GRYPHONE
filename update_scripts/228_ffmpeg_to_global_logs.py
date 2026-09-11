#!/usr/bin/env python3
"""
228. update_scripts/228_ffmpeg_to_global_logs.py
----------------------------------------------------------------------------
Дублирует вывод ffmpeg в глобальные Python-логи (gryphone.log → /logs).

Per-camera логи (manager.add_log → /api/ffmpeg_logs) продолжают работать
как раньше. Классификация:
  • ERROR: error, failed, invalid, refused, timeout, no such, operation not
  • WARNING: warning, dropped, deprecated, corrupt
  • DEBUG: остальные строки
  • SKIP: строки с "frame=" (прогресс-флуд каждую секунду)

ЗАПУСК: python update_scripts/228_ffmpeg_to_global_logs.py
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


INSERT_BLOCK = '''                                    # PATCH-228: дублируем в глобальные логи
                                    low = text.lower()
                                    if text.startswith("frame="):
                                        pass  # прогресс-флуд не логируем
                                    elif any(k in low for k in (
                                        "error", "failed", "invalid", "refused",
                                        "timeout", "no such", "operation not",
                                        "unreachable", "denied",
                                    )):
                                        logger.error("[ffmpeg:%s] %s", route_id, text)
                                    elif any(k in low for k in (
                                        "warning", "dropped", "deprecated",
                                        "corrupt", "truncat",
                                    )):
                                        logger.warning("[ffmpeg:%s] %s", route_id, text)
                                    elif "stream #0" in low or "input #" in low:
                                        logger.info("[ffmpeg:%s] %s", route_id, text)
                                    else:
                                        logger.debug("[ffmpeg:%s] %s", route_id, text)
'''


def main():
    root = find_project_root()
    f = root / "app" / "workers" / "hls_worker.py"

    print("=" * 76)
    print("228: ffmpeg-логи → глобальные /logs")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-228")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "PATCH-228" in c:
        print("  [OK] уже применён")
        return

    # Якорь: блок manager.add_log с двумя аргументами
    # Ищем конец блока — строку с ")" закрывающую add_log(...)
    anchor_lines = [
        "                                    manager.add_log(",
        "                                        route_id,",
        '                                        f"[{time.strftime(\'%H:%M:%S\')}] {text}",',
        "                                    )",
    ]

    # Ищем позицию вставки: после "                                    )"
    lines = c.split("\n")
    insert_idx = None
    for i in range(len(lines)):
        if lines[i].strip() == ")":
            # проверяем контекст: выше должно быть manager.add_log(
            ctx = "\n".join(lines[max(0, i-4):i+1])
            if "manager.add_log(" in ctx and "route_id," in ctx and "strftime" in ctx:
                insert_idx = i + 1
                break

    if insert_idx is None:
        print("  [FAIL] якорь manager.add_log(...) не найден — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # Вставляем блок классификации
    insert_lines = INSERT_BLOCK.rstrip("\n").split("\n")
    for j, il in enumerate(insert_lines):
        lines.insert(insert_idx + j, il)

    c_new = "\n".join(lines)

    # Sanity check
    try:
        compile(c_new, str(f), "exec")
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    f.write_text(c_new, encoding="utf-8")
    print(f"  [OK] блок классификации ffmpeg-строк вставлен в строку {insert_idx + 1}")

    # Smoke: импорт модуля
    import subprocess
    r = subprocess.run(
        [sys.executable, "-c", "import app.workers.hls_worker; print('OK')"],
        cwd=str(root), capture_output=True, text=True, timeout=15,
    )
    if r.returncode != 0 or "OK" not in r.stdout:
        print(f"  [FAIL] импорт падает:")
        print(r.stderr[-500:])
        print("  откат...")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)
    print("  [OK] импорт чистый")

    print()
    print("=" * 76)
    print("✅ PATCH-228 готов! Перезапуск:")
    print()
    print(f"  cd {root} && python main.py")
    print()
    print("Откройте /logs (Ctrl+F5), фильтр ERROR:")
    print("  • [ffmpeg:*-403-..._main] Connection refused: rtsp://...")
    print("  • [ffmpeg:210-..._sub] No such file or directory")
    print()
    print("Фильтр INFO:")
    print("  • [ffmpeg:210-..._main] Input #0, rtsp, from 'rtsp://...'")
    print("  • [ffmpeg:210-..._main] Stream #0:0: Video: h264 ...")
    print()
    print("Фильтр DEBUG — весь вывод ffmpeg")
    print()
    print("⚠️  Per-camera логи (/api/ffmpeg_logs) работают как раньше!")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat(logs): ffmpeg output to global logs (PATCH-228)" \\')
    print('  -m "hls_worker: classify ffmpeg stderr lines in _read_logs()" \\')
    print('  -m "  ERROR: connection refused, invalid data, timeout, etc." \\')
    print('  -m "  WARNING: dropped frames, deprecated options" \\')
    print('  -m "  INFO: Input #0, Stream #0 (camera connect success)" \\')
    print('  -m "  DEBUG: everything else" \\')
    print('  -m "  SKIP: frame=... progress lines (avoid spam)" \\')
    print('  -m "per-camera logs (/api/ffmpeg_logs) preserved" \\')
    print('  -m "now visible on /logs page with level filters"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()