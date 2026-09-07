#!/usr/bin/env python3
"""
187. update_scripts/187_database_lines_fixed.py
----------------------------------------------------------------------------
Повтор построчной правки database.py из PATCH-185 с ВЕРНЫМИ счётчиками
(map=6, а не 8): реальный код использует cameras.append({...}).

ЗАПУСК: python update_scripts/187_database_lines_fixed.py
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


def main():
    root = find_project_root()
    f = root / "app" / "database.py"

    print("=" * 76)
    print("187: database.py построчно (исправленные счётчики)")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-187")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    lines = f.read_text(encoding="utf-8").split("\n")
    out = []
    st = {"cols": 0, "vals": 0, "main": 0, "sub": 0, "select": 0, "map": 0}

    for line in lines:
        s = line.strip()
        ind = line[:len(line) - len(line.lstrip())]

        if s == "(id, name, main_url, sub_url, enabled, comment, audio, location)":
            out.append(ind + "(id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url, enabled, comment, audio, location)")
            st["cols"] += 1; continue

        if s == "VALUES (?, ?, ?, ?, ?, ?, ?, ?)":
            out.append(ind + "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
            st["vals"] += 1; continue

        if s == 'cam.get("main_url", ""),':
            out.append(ind + 'cam.get("login", ""),')
            out.append(ind + 'cam.get("pass", ""),')
            out.append(ind + 'cam.get("ipaddress", ""),')
            out.append(ind + 'cam.get("port", "554"),')
            out.append(ind + 'str(cam.get("main_url", "")).lstrip("/"),  # PATCH-187')
            st["main"] += 1; continue

        if s == 'cam.get("sub_url", ""),':
            out.append(ind + 'str(cam.get("sub_url", "")).lstrip("/"),')
            out.append(ind + 'str(cam.get("sub2_url", "")).lstrip("/"),')
            st["sub"] += 1; continue

        if s == "cam.get('main_url', ''),":
            out.append(ind + "cam.get('login', ''),")
            out.append(ind + "cam.get('pass', ''),")
            out.append(ind + "cam.get('ipaddress', ''),")
            out.append(ind + "cam.get('port', '554'),")
            out.append(ind + "str(cam.get('main_url', '')).lstrip('/'),  # PATCH-187")
            st["main"] += 1; continue

        if s == "cam.get('sub_url', ''),":
            out.append(ind + "str(cam.get('sub_url', '')).lstrip('/'),")
            out.append(ind + "str(cam.get('sub2_url', '')).lstrip('/'),")
            st["sub"] += 1; continue

        if "SELECT id, name, main_url, sub_url, enabled, comment, audio, location" in s:
            out.append(line.replace(
                "SELECT id, name, main_url, sub_url, enabled, comment, audio, location",
                "SELECT id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url, enabled, comment, audio, location"))
            st["select"] += 1; continue

        if s == "'main_url': row[2],":
            out.append(ind + "'login': row[2],")
            out.append(ind + "'pass': row[3],")
            out.append(ind + "'ipaddress': row[4],")
            out.append(ind + "'port': row[5],")
            out.append(ind + "'main_url': row[6],")
            st["map"] += 1; continue

        if s == "'sub_url': row[3],":
            out.append(ind + "'sub_url': row[7],")
            out.append(ind + "'sub2_url': row[8],")
            st["map"] += 1; continue

        if s == "'enabled': bool(row[4]),":
            out.append(ind + "'enabled': bool(row[9]),"); st["map"] += 1; continue
        if s == "'comment': row[5],":
            out.append(ind + "'comment': row[10],"); st["map"] += 1; continue
        if s == "'audio': bool(row[6]),":
            out.append(ind + "'audio': bool(row[11]),"); st["map"] += 1; continue
        if s == "'location': row[7]":
            out.append(ind + "'location': row[12]"); st["map"] += 1; continue

        out.append(line)

    print(f"  [OK] замен: cols={st['cols']} vals={st['vals']} main={st['main']} "
          f"sub={st['sub']} select={st['select']} map={st['map']}")

    ok = (st["cols"] == 2 and st["vals"] == 2 and st["main"] == 2
          and st["sub"] == 2 and st["select"] == 1 and st["map"] == 6)
    content = "\n".join(out)

    if ok:
        try:
            compile(content, str(f), "exec")
            f.write_text(content, encoding="utf-8")
            print("  [OK] Сохранено")
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)
    else:
        print("  [FAIL] счётчики не сошлись — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ database.py полностью на новой схеме!")
    print()
    print("  1. rm data/gryphone.db   (ложная пустая БД)")
    print("  2. python main.py")
    print("  3. Монитор: потоки должны работать")
    print()
    print("⚠️  Камеры из UI НЕ сохранять до PATCH-188 (форма старая)")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ потоков — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "refactor: camera RTSP URL split into parts (PATCH-184..187)" \\')
    print('  -m "DB: login/pass/ipaddress/port/main_url/sub_url/sub2_url + migration (24 cams)" \\')
    print('  -m "models.Camera: build_url() assembles rtsp on server, lstrip leading /" \\')
    print('  -m "database.py: INSERT/SELECT/mapping on new columns; legacy rtsp auto-split" \\')
    print('  -m "stream_manager: uses build_url()"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()