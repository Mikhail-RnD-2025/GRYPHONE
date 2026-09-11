#!/usr/bin/env python3
"""
214.1 update_scripts/214_1_hls_worker_reconnect.py
----------------------------------------------------------------------------
hls_worker.py: при переподключении (итерация while True) статус «недоступна»
сохраняется, меняется только msg на «Переподключение...».
Если предыдущий статус был другим — ведём себя как раньше («подключение»).

ЗАПУСК: python update_scripts/214_1_hls_worker_reconnect.py
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


OLD = '                manager.set_status(route_id, "подключение", "Запуск потока...")'

NEW = """                # PATCH-214.1: не сбрасываем «недоступна» при переподключении.
                # Если предыдущий state = "недоступна" (хост/кодек/ошибка),
                # оставляем его, меняя только msg. Иначе — как раньше.
                _prev = manager.get_status(route_id) or {}
                if _prev.get("state") == "недоступна":
                    manager.set_status(route_id, "недоступна", "Переподключение...")
                else:
                    manager.set_status(route_id, "подключение", "Запуск потока...")"""


def main():
    root = find_project_root()
    f = root / "app" / "workers" / "hls_worker.py"

    print("=" * 76)
    print("214.1: hls_worker — стабильный статус «недоступна» при переподключении")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-2141")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "PATCH-214" in c:
        print("  [OK] уже применён")
    elif OLD in c:
        c = c.replace(OLD, NEW, 1)
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] строка 127 обёрнута: «недоступна» сохраняется при переподключении")
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)
    else:
        print("  [FAIL] точный якорь не найден — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("--- итоговая строка 127-133 ---")
    lines = f.read_text(encoding="utf-8").split("\n")
    for i in range(126, min(134, len(lines))):
        print(f"  {i+1:3}: {lines[i]}")

    print()
    print("=" * 76)
    print("✅ Готово! Перезапустите сервер (backend изменён):")
    print()
    print(f"  cd {root} && python main.py")
    print()
    print("Ожидаемое поведение:")
    print("  • При старте: state = «подключение» (первый запуск)")
    print("  • Если хост недоступен: state = «недоступна», msg = «Хост недоступен»")
    print("  • Через 10 сек переподключение: state остаётся «недоступна»,")
    print("    msg = «Переподключение...» (НЕ мигает жёлтым)")
    print("  • UI показывает стабильные 🔴 вместо 🟡↔🔴")
    print("=" * 76)
    print()
    print("📦 Коммит (соединить с 214):")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix(workers): keep «недоступна» state on reconnect (PATCH-214.1)" \\')
    print('  -m "hls_worker: inside while True loop, if prev state=недоступна," \\')
    print('  -m "keep state, only change msg to «Переподключение...»" \\')
    print('  -m "prevents yellow flicker in /status dashboard"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()