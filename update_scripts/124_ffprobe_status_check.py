#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
124v6: Статус на основе ffprobe (поиск вызова, а не импорта)
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    worker = project_root / "app" / "workers" / "hls_worker.py"

    print("=" * 76)
    print("124 v6: Статус на основе ffprobe (поиск вызова)")
    print("=" * 76)
    print()

    backup = worker.with_suffix(".py.bak-124")
    if backup.exists():
        worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  [OK] Восстановлено из {backup.name}")

    content = worker.read_text(encoding="utf-8")

    if "PATCH-124v6" in content:
        print("  [OK] Патч уже применён")
        return

    lines = content.split("\n")

    # ШАГ 1: найти ВЫЗОВ probe_camera (строка содержит probe_camera И url)
    probe_idx = None
    for i, line in enumerate(lines):
        if "probe_camera" in line and "url" in line:
            probe_idx = i
            break

    if probe_idx is None:
        print("  [ERROR] Вызов probe_camera не найден.")
        print("  Пришлите: sed -n '70,110p' app/workers/hls_worker.py")
        sys.exit(1)
    print(f"  [OK] Вызов probe_camera найден (строка {probe_idx + 1}): "
          f"{lines[probe_idx].strip()}")

    # ШАГ 2: найти except после вызова
    except_idx = None
    for i in range(probe_idx, len(lines)):
        if lines[i].strip().startswith("except"):
            except_idx = i
            break

    if except_idx is None:
        print("  [ERROR] except не найден после probe")
        sys.exit(1)
    print(f"  [OK] except найден (строка {except_idx + 1}): "
          f"{lines[except_idx].strip()}")

    # ШАГ 3: найти конец тела except
    except_indent = len(lines[except_idx]) - len(lines[except_idx].lstrip())
    last_body = except_idx
    for i in range(except_idx + 1, len(lines)):
        s = lines[i]
        if s.strip() == "":
            continue
        cur = len(s) - len(s.lstrip())
        if cur > except_indent:
            last_body = i
        else:
            break
    print(f"  [OK] Конец тела except (строка {last_body + 1})")

    # ШАГ 4: блок для вставки
    ind = " " * except_indent
    ind4 = " " * (except_indent + 4)
    ind8 = " " * (except_indent + 8)

    insert_lines = [
        f"{ind}# PATCH-124v6: устанавливаем статус на основе ffprobe",
        f"{ind}if codec and codec != \"unknown\":",
        f"{ind4}logger.info(\"✅ %s: поток доступен (codec=%s)\", route_id, codec)",
        f"{ind4}manager.set_status(route_id, \"в_сети\", \"Поток активен\",",
        f"{ind8}metrics={{\"codec\": codec, \"profile\": profile}})",
        f"{ind}else:",
        f"{ind4}logger.warning(\"⚠️ %s: поток недоступен (codec=unknown)\", route_id)",
        f"{ind4}manager.set_status(route_id, \"недоступна\", \"Кодек не определён\")",
        f"{ind4}await asyncio.sleep(min(backoff * 2, 15))",
        f"{ind4}backoff = min(backoff * 2, 15)",
        f"{ind4}continue",
    ]

    lines[last_body + 1:last_body + 1] = insert_lines
    content = "\n".join(lines)

    # ШАГ 5: проверка синтаксиса
    print()
    print("--- Проверка синтаксиса ---")
    try:
        compile(content, str(worker), "exec")
        print("  [OK] Синтаксис корректен")
    except SyntaxError as e:
        print(f"  [FAIL] Ошибка: {e}")
        worker.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        print("  Файл восстановлен из бэкапа")
        print()
        print("  Пришлите вывод для ручной правки:")
        print("    sed -n '70,110p' app/workers/hls_worker.py")
        sys.exit(1)

    worker.write_text(content, encoding="utf-8")
    print("  [OK] Файл сохранён")
    print()

    print("=" * 76)
    print("✅ Готово! Статус устанавливается на основе ffprobe.")
    print()
    print("Перезапустите сервер:")
    print("  python main.py")
    print()
    print("В логах через 3-9 сек:")
    print("  ✅ 210-P-GAVw-005_main: поток доступен (codec=h264)")
    print("=" * 76)


if __name__ == "__main__":
    main()