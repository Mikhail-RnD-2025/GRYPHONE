#!/usr/bin/env python3
"""
185. update_scripts/185_db_autodetect_and_database_lines.py
----------------------------------------------------------------------------
  • Автопоиск файла БД: любой *.db в проекте, где в cameras есть main_url
  • Миграция: пересоздание таблицы с login/pass/ipaddress/port/main_url/sub_url/sub2_url
    (парсинг старых полных URL), восстановление индексов
  • database.py: построчная замена INSERT/SELECT/маппинга (нечувствительно к формату)
  • models.py: legacy-поддержка — если main_url пришёл полным rtsp://, разбираем на части

ЗАПУСК: python update_scripts/185_db_autodetect_and_database_lines.py
"""

import sys
import sqlite3
from pathlib import Path
from urllib.parse import urlparse


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


def find_db(root):
    """Ищет *.db, где в таблице cameras есть колонка main_url."""
    candidates = []
    for p in root.rglob("*.db"):
        if "node_modules" in str(p):
            continue
        try:
            conn = sqlite3.connect(str(p))
            cols = [r[1] for r in conn.execute("PRAGMA table_info(cameras)")]
            n = 0
            if cols:
                n = conn.execute("SELECT COUNT(*) FROM cameras").fetchone()[0]
            conn.close()
            if "main_url" in cols:
                return p, n
            candidates.append((p, cols))
        except sqlite3.Error:
            continue
    return None, candidates


def parse_rtsp_url(url):
    if not url or not url.strip():
        return None
    try:
        p = urlparse(url.strip())
        if p.scheme.lower() != 'rtsp':
            return None
        path = p.path.lstrip('/')
        if p.query:
            path += '?' + p.query
        return {
            'login': p.username or '',
            'pass': p.password or '',
            'ipaddress': p.hostname or '',
            'port': str(p.port) if p.port else '554',
            'path': path
        }
    except Exception as e:
        print(f"  [WARN] парсинг {url}: {e}")
        return None


def migrate_db(db_file):
    print(f"--- миграция БД: {db_file} ---")
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT id, name, main_url, sub_url, enabled, comment, audio, location FROM cameras")
    old = cur.fetchall()
    print(f"  [OK] камер: {len(old)}")

    rows = []
    for cam_id, name, main_url, sub_url, enabled, comment, audio, location in old:
        m = parse_rtsp_url(main_url)
        s = parse_rtsp_url(sub_url) if sub_url else None
        if m:
            login, pw, ip, port, main_path = m['login'], m['pass'], m['ipaddress'], m['port'], m['path']
        else:
            print(f"  [WARN] {cam_id}: main_url не распознан: {main_url!r}")
            login = pw = ip = port = main_path = ''
        rows.append((
            cam_id, name, login, pw, ip, port,
            main_path,
            s['path'] if s else '',
            '',
            enabled, comment, audio, location
        ))

    cur.executescript("""
        DROP TABLE IF EXISTS cameras_new;
        CREATE TABLE cameras_new (
            id TEXT PRIMARY KEY,
            name TEXT,
            login TEXT,
            pass TEXT,
            ipaddress TEXT,
            port TEXT,
            main_url TEXT,
            sub_url TEXT,
            sub2_url TEXT,
            enabled INTEGER DEFAULT 1,
            comment TEXT,
            audio INTEGER DEFAULT 1,
            location TEXT
        );
    """)
    cur.executemany("""
        INSERT INTO cameras_new
        (id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url,
         enabled, comment, audio, location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    cur.execute("DROP TABLE cameras")
    cur.execute("ALTER TABLE cameras_new RENAME TO cameras")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cameras_enabled ON cameras(enabled)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cameras_name ON cameras(name)")
    conn.commit()
    conn.close()
    print("  [OK] таблица пересоздана + индексы восстановлены")
    return True


def patch_database(f):
    print("--- database.py (построчно) ---")
    b = f.with_suffix(".py.bak-185")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    lines = f.read_text(encoding="utf-8").split("\n")
    out = []
    stats = {"cols": 0, "vals": 0, "main": 0, "sub": 0, "select": 0, "map": 0}

    for line in lines:
        s = line.strip()
        ind = line[:len(line) - len(line.lstrip())]

        # колонки INSERT (2 места)
        if s == "(id, name, main_url, sub_url, enabled, comment, audio, location)":
            out.append(ind + "(id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url, enabled, comment, audio, location)")
            stats["cols"] += 1
            continue
        # VALUES (2 места, ровно 8 плейсхолдеров)
        if s == "VALUES (?, ?, ?, ?, ?, ?, ?, ?)":
            out.append(ind + "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
            stats["vals"] += 1
            continue
        # параметры _populate (двойные кавычки)
        if s == 'cam.get("main_url", ""),':
            out.append(ind + 'cam.get("login", ""),')
            out.append(ind + 'cam.get("pass", ""),')
            out.append(ind + 'cam.get("ipaddress", ""),')
            out.append(ind + 'cam.get("port", "554"),')
            out.append(ind + 'str(cam.get("main_url", "")).lstrip("/"),  # PATCH-185')
            stats["main"] += 1
            continue
        if s == 'cam.get("sub_url", ""),':
            out.append(ind + 'str(cam.get("sub_url", "")).lstrip("/"),')
            out.append(ind + 'str(cam.get("sub2_url", "")).lstrip("/"),')
            stats["sub"] += 1
            continue
        # параметры save_cameras_list (одинарные кавычки)
        if s == "cam.get('main_url', ''),":
            out.append(ind + "cam.get('login', ''),")
            out.append(ind + "cam.get('pass', ''),")
            out.append(ind + "cam.get('ipaddress', ''),")
            out.append(ind + "cam.get('port', '554'),")
            out.append(ind + "str(cam.get('main_url', '')).lstrip('/'),  # PATCH-185")
            stats["main"] += 1
            continue
        if s == "cam.get('sub_url', ''),":
            out.append(ind + "str(cam.get('sub_url', '')).lstrip('/'),")
            out.append(ind + "str(cam.get('sub2_url', '')).lstrip('/'),")
            stats["sub"] += 1
            continue
        # SELECT в get_all_cameras
        if "SELECT id, name, main_url, sub_url, enabled, comment, audio, location" in s:
            out.append(line.replace(
                "SELECT id, name, main_url, sub_url, enabled, comment, audio, location",
                "SELECT id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url, enabled, comment, audio, location"))
            stats["select"] += 1
            continue
        # маппинг строк в dict
        if s == "'main_url': row[2],":
            out.append(ind + "'login': row[2],")
            out.append(ind + "'pass': row[3],")
            out.append(ind + "'ipaddress': row[4],")
            out.append(ind + "'port': row[5],")
            out.append(ind + "'main_url': row[6],")
            stats["map"] += 1
            continue
        if s == "'sub_url': row[3],":
            out.append(ind + "'sub_url': row[7],")
            out.append(ind + "'sub2_url': row[8],")
            stats["map"] += 1
            continue
        if s == "'enabled': bool(row[4]),":
            out.append(ind + "'enabled': bool(row[9]),"); stats["map"] += 1; continue
        if s == "'comment': row[5],":
            out.append(ind + "'comment': row[10],"); stats["map"] += 1; continue
        if s == "'audio': bool(row[6]),":
            out.append(ind + "'audio': bool(row[11]),"); stats["map"] += 1; continue
        if s == "'location': row[7]":
            out.append(ind + "'location': row[12]"); stats["map"] += 1; continue

        out.append(line)

    print(f"  [OK] замен: cols={stats['cols']} vals={stats['vals']} main={stats['main']} "
          f"sub={stats['sub']} select={stats['select']} map={stats['map']}")

    ok = (stats["cols"] == 2 and stats["vals"] == 2 and stats["main"] == 2
          and stats["sub"] == 2 and stats["select"] == 1 and stats["map"] == 8)
    content = "\n".join(out)
    if ok:
        try:
            compile(content, str(f), "exec")
            f.write_text(content, encoding="utf-8")
            print("  [OK] Сохранено")
            return True
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
    else:
        print("  [FAIL] не все якори найдены — откат")
    f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
    return False


def patch_models_legacy(f):
    print("--- models.py: legacy-парсинг полных rtsp:// ---")
    c = f.read_text(encoding="utf-8")
    if "PATCH-185" in c:
        print("  [OK] Уже есть")
        return True
    old = """    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["Camera"]:
        if not isinstance(raw, dict):
            return None
        cam_id = raw.get("id")
        ipaddress = raw.get("ipaddress")
        main_url = raw.get("main_url")"""
    new = """    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["Camera"]:
        if not isinstance(raw, dict):
            return None
        raw = cls._split_legacy_urls(raw)  # PATCH-185
        cam_id = raw.get("id")
        ipaddress = raw.get("ipaddress")
        main_url = raw.get("main_url")"""
    if old not in c:
        print("  [WARN] якорь from_raw не найден")
        return False

    helper = '''
    @staticmethod
    def _split_legacy_urls(raw: Dict[str, Any]) -> Dict[str, Any]:
        """PATCH-185: если main_url/sub_url пришли полными rtsp:// — разобрать на части."""
        from urllib.parse import urlparse
        out = dict(raw)
        for key in ("main_url", "sub_url"):
            val = out.get(key) or ""
            if isinstance(val, str) and val.strip().lower().startswith("rtsp://"):
                p = urlparse(val.strip())
                out["login"] = out.get("login") or (p.username or "")
                out["pass"] = out.get("pass") or (p.password or "")
                out["ipaddress"] = out.get("ipaddress") or (p.hostname or "")
                out["port"] = out.get("port") or (str(p.port) if p.port else "554")
                path = p.path.lstrip("/")
                if p.query:
                    path += "?" + p.query
                out[key] = path
        return out
'''
    # вставляем helper перед from_raw
    anchor = "    @classmethod\n    def from_raw(cls, raw: Dict[str, Any]) -> Optional[\"Camera\"]:"
    c = c.replace(anchor, helper + "\n" + anchor, 1)
    c = c.replace(old, new, 1)
    try:
        compile(c, str(f), "exec")
        f.write_text(c, encoding="utf-8")
        print("  [OK] legacy-парсинг добавлен")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e}")
        return False


def main():
    root = find_project_root()
    print(f"  [OK] Корень проекта: {root}")
    print()
    print("=" * 76)
    print("185: автопоиск БД + миграция + database.py построчно")
    print("=" * 76)
    print()

    db_file, info = find_db(root)
    if db_file is None:
        print(f"  [FAIL] БД с cameras.main_url не найдена; кандидаты: {info}")
        sys.exit(1)
    print(f"  [OK] Найдена БД: {db_file}")

    ok = True
    ok &= migrate_db(db_file)
    ok &= patch_database(root / "app" / "database.py")
    ok &= patch_models_legacy(root / "app" / "models.py")

    # предупреждение о пустой ложной БД
    fake = root / "data" / "gryphone.db"
    if fake.exists():
        try:
            conn = sqlite3.connect(str(fake))
            cols = [r[1] for r in conn.execute("PRAGMA table_info(cameras)")]
            conn.close()
            if not cols:
                print(f"  [WARN] {fake} — пустая ложная БД (создана старыми патчами). Удалите: rm data/gryphone.db")
        except sqlite3.Error:
            pass

    if not ok:
        print()
        print("[FAIL] часть шагов не прошла")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово!")
    print("  1. Перезапустить сервер: python main.py")
    print("  2. Монитор: потоки должны работать (URL собирается сервером)")
    print("  3. НЕ сохраняйте камеры из UI до PATCH-186 (фронтенд ещё шлёт старые поля)")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "refactor: camera RTSP URL split into parts (PATCH-184,185)" \\')
    print('  -m "DB: login/pass/ipaddress/port/main_url/sub_url/sub2_url + migration" \\')
    print('  -m "models.Camera: build_url() assembles rtsp on server, lstrip leading /" \\')
    print('  -m "database.py: line-based INSERT/SELECT update; legacy rtsp:// auto-split" \\')
    print('  -m "stream_manager: uses build_url()"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()