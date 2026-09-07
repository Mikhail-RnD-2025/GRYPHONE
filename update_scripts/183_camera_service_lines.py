#!/usr/bin/env python3
"""
183. update_scripts/183_camera_service_lines.py
----------------------------------------------------------------------------
Построчное удаление _default_set из camera_service.py:
  • не зависит от точных пробелов/переносов
  • при синтакс-ошибке печатает проблемную область (диагностика)

ЗАПУСК: python update_scripts/183_camera_service_lines.py
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


def transform(content):
    lines = content.split("\n")
    out = []
    i = 0
    stats = {"init": 0, "load": 0, "method": 0, "save": 0, "cur": 0}
    while i < len(lines):
        s = lines[i].strip()

        # 1. __init__: self._default_set: str = ""
        if s == 'self._default_set: str = ""':
            i += 1
            stats["init"] += 1
            continue

        # 2. _load: блок от "self._default_set = (" до "self._current_set = self._default_set"
        if s == "self._default_set = (":
            while i < len(lines) and lines[i].strip() != "self._current_set = self._default_set":
                i += 1
            i += 1
            out.append("        # PATCH-183: сервер НЕ хранит выбор — клиент синхронизирует сам")
            out.append('        self._current_set = ""')
            stats["load"] += 1
            continue

        # 3. метод default_set_id целиком (до return + пустая строка)
        if s == "def default_set_id(self) -> str:":
            while i < len(lines) and lines[i].strip() != "return self._default_set":
                i += 1
            i += 1
            if i < len(lines) and lines[i].strip() == "":
                i += 1
            stats["method"] += 1
            continue

        # 4. save_sets: строка с raw.get("default_set"...)
        if s == 'self._default_set = raw.get("default_set", "") or self._default_set':
            i += 1
            stats["save"] += 1
            continue

        # 5. оставшийся "self._current_set = self._default_set" (save_sets, 12 пробелов)
        if s == "self._current_set = self._default_set":
            out.append('            self._current_set = ""')
            i += 1
            stats["cur"] += 1
            continue

        out.append(lines[i])
        i += 1
    return "\n".join(out), stats


def main():
    root = find_project_root()
    f = root / "app" / "services" / "camera_service.py"

    print("=" * 76)
    print("183: camera_service.py — построчное удаление _default_set")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-183")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "PATCH-183" in c:
        print("  [OK] Уже применён")
        return
    if "_default_set" not in c:
        print("  [OK] _default_set уже удалён")
        return

    new, stats = transform(c)
    print(f"  [OK] замен: init={stats['init']} load={stats['load']} "
          f"method={stats['method']} save={stats['save']} cur={stats['cur']}")

    if stats["load"] != 1 or stats["method"] != 1:
        print("  [FAIL] не все блоки найдены — откат")
        sys.exit(1)

    try:
        compile(new, str(f), "exec")
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — строка {e.lineno}")
        print("  --- проблемная область ---")
        ls = new.split("\n")
        for n in range(max(0, e.lineno - 8), min(len(ls), e.lineno + 8)):
            print(f"  {n + 1:4d}| {ls[n]}")
        print("  --------------------------")
        print("  Пришлите этот вывод — исправлю якорь")
        sys.exit(1)

    f.write_text(new, encoding="utf-8")
    print("  [OK] Сохранено")

    print()
    print("=" * 76)
    print("✅ camera_service.py очищен от _default_set")
    print()
    print("  Перезапустить сервер: python main.py")
    print("  (frontend уже собран с PATCH-182)")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "refactor: remove is_default/default_set + localStorage set choice (PATCH-182,183)" \\')
    print('  -m "schema+DB: is_default column and index removed" \\')
    print('  -m "database.py: INSERT/SELECT without is_default, no default_set key" \\')
    print('  -m "camera_service: no _default_set; server stores nothing (PATCH-183)" \\')
    print('  -m "api: GET /api/sets returns current_set" \\')
    print('  -m "Header: last set in localStorage, server synced via switchSet"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()