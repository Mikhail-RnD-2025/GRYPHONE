#!/usr/bin/env python3
"""
184. update_scripts/184_camera_url_parts_v2.py
----------------------------------------------------------------------------
Разделение RTSP URL на части (правильные имена колонок):
  • БД: login, pass, ipaddress, port, main_url, sub_url, sub2_url
  • Модель Camera: те же поля + build_url()
  • stream_manager: использует cam.build_url('main_url')
  • Миграция: парсинг старых main_url/sub_url на части

ЗАПУСК: python update_scripts/184_camera_url_parts_v2.py
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


def parse_rtsp_url(url):
    """Парсит RTSP URL на части. Возвращает dict или None."""
    if not url or not url.strip():
        return None
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme.lower() != 'rtsp':
            return None

        login = parsed.username or ''
        password = parsed.password or ''
        ipaddress = parsed.hostname or ''
        port = str(parsed.port) if parsed.port else '554'

        path = parsed.path.lstrip('/')
        if parsed.query:
            path += '?' + parsed.query

        return {
            'login': login,
            'pass': password,
            'ipaddress': ipaddress,
            'port': port,
            'path': path
        }
    except Exception as e:
        print(f"  [WARN] Не удалось распарсить {url}: {e}")
        return None


def migrate_db(db_file):
    print("--- миграция живой БД ---")
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(cameras)")
    cols = [r[1] for r in cur.fetchall()]

    if "main_url" not in cols:
        print("  [FAIL] main_url не найден — откат")
        conn.close()
        return False

    if "login" in cols and "sub2_url" in cols:
        print("  [OK] БД уже мигрирована")
        conn.close()
        return True

    # Читаем старые данные
    cur.execute("SELECT id, name, main_url, sub_url, enabled, comment, audio, location FROM cameras")
    old_cams = cur.fetchall()
    print(f"  [OK] Прочитано {len(old_cams)} камер")

    # Парсим URL
    new_cams = []
    for row in old_cams:
        cam_id, name, main_url, sub_url, enabled, comment, audio, location = row

        main_parts = parse_rtsp_url(main_url)
        sub_parts = parse_rtsp_url(sub_url) if sub_url else None

        if main_parts:
            login = main_parts['login']
            password = main_parts['pass']
            ipaddress = main_parts['ipaddress']
            port = main_parts['port']
            main_path = main_parts['path']
        else:
            print(f"  [WARN] Камера {cam_id}: не удалось распарсить main_url={main_url}")
            login = password = ipaddress = port = main_path = ''

        sub_path = sub_parts['path'] if sub_parts else ''
        sub2_path = ''

        new_cams.append((
            cam_id, name, login, password, ipaddress, port,
            main_path, sub_path, sub2_path,
            enabled, comment, audio, location
        ))

    print(f"  [OK] Распарсено {len([c for c in new_cams if c[6]])} основных потоков")

    # Пересоздаём таблицу
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
        (id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url, enabled, comment, audio, location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, new_cams)

    cur.execute("DROP TABLE cameras")
    cur.execute("ALTER TABLE cameras_new RENAME TO cameras")
    conn.commit()
    conn.close()

    print("  [OK] Таблица пересоздана: login, pass, ipaddress, port, main_url, sub_url, sub2_url")
    return True


def patch_schema(f):
    print("--- schema.sql ---")
    lines = f.read_text(encoding="utf-8").split("\n")
    out, in_cameras = [], False
    for line in lines:
        if "CREATE TABLE IF NOT EXISTS cameras" in line:
            in_cameras = True
            out.append(line)
            continue
        if in_cameras:
            if line.strip() == ");":
                out.append("""    -- PATCH-184: части RTSP URL (login/pass/ip/port + пути потоков)
    login TEXT,
    pass TEXT,
    ipaddress TEXT,
    port TEXT,
    main_url TEXT,
    sub_url TEXT,
    sub2_url TEXT,
    -- Включена ли камера (0=выключена, 1=включена)
    enabled INTEGER DEFAULT 1,
    -- Комментарий/описание камеры (например, расположение)
    comment TEXT,
    -- Включать ли аудио при захвате (0=нет, 1=да)
    audio INTEGER DEFAULT 1,
    -- Местоположение камеры (физическое: этаж, корпус, комната)
    location TEXT
);""")
                out.append(line)
                in_cameras = False
                continue
            continue
        out.append(line)

    f.write_text("\n".join(out), encoding="utf-8")
    print("  [OK] schema.sql: новые колонки")
    return True


def patch_models(f):
    print("--- models.py ---")
    b = f.with_suffix(".py.bak-184")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    old = """@dataclass
class Camera:
    \"\"\"Модель камеры наблюдения.\"\"\"

    id: str
    name: str
    main_url: str
    sub_url: str = ""
    enabled: bool = True
    comment: str = ""
    audio: bool = True
    location: str = ""

    @property
    def main_route_id(self) -> str:
        \"\"\"Идентификатор основного потока (английский суффикс).\"\"\"
        return f"{self.id}_main"

    @property
    def sub_route_id(self) -> str:
        \"\"\"Идентификатор субпотока (английский суффикс).\"\"\"
        return f"{self.id}_sub"

    @property
    def has_sub_stream(self) -> bool:
        \"\"\"Проверяет, есть ли отдельный субпоток.\"\"\"
        return bool(self.sub_url) and self.sub_url.strip() != "" and \\
               self.sub_url != self.main_url

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["Camera"]:
        if not isinstance(raw, dict):
            return None
        cam_id = raw.get("id")
        main_url = raw.get("main_url")
        if not cam_id or not main_url:
            return None
        return cls(
            id=str(cam_id).strip(),
            name=str(raw.get("name", cam_id)).strip(),
            main_url=str(main_url).strip(),
            sub_url=str(raw.get("sub_url", "")).strip(),
            enabled=bool(raw.get("enabled", True)),
            comment=str(raw.get("comment", "")).strip(),
            audio=bool(raw.get("audio", True)),
            location=str(raw.get("location", "")).strip(),
        )"""

    new = """@dataclass
class Camera:
    \"\"\"Модель камеры наблюдения.\"\"\"

    id: str
    name: str
    login: str = ""
    pass_: str = field(default="", metadata={"alias": "pass"})
    ipaddress: str = ""
    port: str = "554"
    main_url: str = ""
    sub_url: str = ""
    sub2_url: str = ""
    enabled: bool = True
    comment: str = ""
    audio: bool = True
    location: str = ""

    @property
    def main_route_id(self) -> str:
        return f"{self.id}_main"

    @property
    def sub_route_id(self) -> str:
        return f"{self.id}_sub"

    @property
    def has_sub_stream(self) -> bool:
        return bool(self.sub_url) and self.sub_url.strip() != "" and self.sub_url != self.main_url

    def build_url(self, stream_type: str = "main_url") -> str:
        \"\"\"PATCH-184: собирает полный RTSP URL на сервере.\"\"\"
        path = getattr(self, stream_type, "")
        if not path:
            return ""

        auth = ""
        if self.login:
            auth = self.login
            if self.pass_:
                auth += f":{self.pass_}"
            auth += "@"

        # Гарантируем ровно один / между портом и путём
        path = path.lstrip('/')
        return f"rtsp://{auth}{self.ipaddress}:{self.port}/{path}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if 'pass_' in d:
            d['pass'] = d.pop('pass_')
        return d

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional["Camera"]:
        if not isinstance(raw, dict):
            return None
        cam_id = raw.get("id")
        ipaddress = raw.get("ipaddress")
        main_url = raw.get("main_url")
        if not cam_id or not ipaddress or not main_url:
            return None
        return cls(
            id=str(cam_id).strip(),
            name=str(raw.get("name", cam_id)).strip(),
            login=str(raw.get("login", "")).strip(),
            pass_=str(raw.get("pass", "")).strip(),
            ipaddress=str(ipaddress).strip(),
            port=str(raw.get("port", "554")).strip(),
            main_url=str(main_url).strip().lstrip('/'),  # PATCH-184: обрезка ведущего /
            sub_url=str(raw.get("sub_url", "")).strip().lstrip('/'),
            sub2_url=str(raw.get("sub2_url", "")).strip().lstrip('/'),
            enabled=bool(raw.get("enabled", True)),
            comment=str(raw.get("comment", "")).strip(),
            audio=bool(raw.get("audio", True)),
            location=str(raw.get("location", "")).strip(),
        )"""

    if old in c:
        c = c.replace(old, new, 1)
        if "from dataclasses import dataclass" in c and "field" not in c:
            c = c.replace("from dataclasses import dataclass", "from dataclasses import dataclass, field")
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] Camera модель обновлена")
            return True
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
    else:
        print("  [FAIL] якорь не найден — откат")

    f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
    return False


def patch_database(f):
    print("--- database.py ---")
    b = f.with_suffix(".py.bak-184")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    # _populate_from_json
    old = """                    cursor.execute(\"\"\"
                        INSERT OR REPLACE INTO cameras
                        (id, name, main_url, sub_url, enabled, comment, audio, location)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    \"\"\", (
                        cam.get("id", ""),
                        cam.get("name", ""),
                        cam.get("main_url", ""),
                        cam.get("sub_url", ""),
                        1 if cam.get("enabled", True) else 0,
                        cam.get("comment", ""),
                        1 if cam.get("audio", True) else 0,
                        cam.get("location", "")
                    ))"""
    new = """                    cursor.execute(\"\"\"
                        INSERT OR REPLACE INTO cameras
                        (id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url, enabled, comment, audio, location)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    \"\"\", (
                        cam.get("id", ""),
                        cam.get("name", ""),
                        cam.get("login", ""),
                        cam.get("pass", ""),
                        cam.get("ipaddress", ""),
                        cam.get("port", "554"),
                        str(cam.get("main_url", "")).lstrip('/'),  # PATCH-184
                        str(cam.get("sub_url", "")).lstrip('/'),
                        str(cam.get("sub2_url", "")).lstrip('/'),
                        1 if cam.get("enabled", True) else 0,
                        cam.get("comment", ""),
                        1 if cam.get("audio", True) else 0,
                        cam.get("location", "")
                    ))"""
    if old in c:
        c = c.replace(old, new, 1);
        n += 1
        print("  [OK] _populate: INSERT с новыми колонками")

    # get_all_cameras
    old = """        cursor.execute(\"\"\"
            SELECT id, name, main_url, sub_url, enabled, comment, audio, location
            FROM cameras
        \"\"\")
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                'id': row[0],
                'name': row[1],
                'main_url': row[2],
                'sub_url': row[3],
                'enabled': bool(row[4]),
                'comment': row[5],
                'audio': bool(row[6]),
                'location': row[7]
            }
            for row in rows
        ]"""
    new = """        cursor.execute(\"\"\"
            SELECT id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url, enabled, comment, audio, location
            FROM cameras
        \"\"\")
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                'id': row[0],
                'name': row[1],
                'login': row[2],
                'pass': row[3],
                'ipaddress': row[4],
                'port': row[5],
                'main_url': row[6],
                'sub_url': row[7],
                'sub2_url': row[8],
                'enabled': bool(row[9]),
                'comment': row[10],
                'audio': bool(row[11]),
                'location': row[12]
            }
            for row in rows
        ]"""
    if old in c:
        c = c.replace(old, new, 1);
        n += 1
        print("  [OK] get_all_cameras: SELECT с новыми колонками")

    # save_cameras_list
    old = """        cursor.execute("DELETE FROM cameras")
        for cam in cameras:
            cursor.execute(\"\"\"
                INSERT OR REPLACE INTO cameras
                (id, name, main_url, sub_url, enabled, comment, audio, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            \"\"\", (
                cam.get('id', ''),
                cam.get('name', ''),
                cam.get('main_url', ''),
                cam.get('sub_url', ''),
                1 if cam.get('enabled', True) else 0,
                cam.get('comment', ''),
                1 if cam.get('audio', True) else 0,
                cam.get('location', '')
            ))"""
    new = """        cursor.execute("DELETE FROM cameras")
        for cam in cameras:
            cursor.execute(\"\"\"
                INSERT OR REPLACE INTO cameras
                (id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url, enabled, comment, audio, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            \"\"\", (
                cam.get('id', ''),
                cam.get('name', ''),
                cam.get('login', ''),
                cam.get('pass', ''),
                cam.get('ipaddress', ''),
                cam.get('port', '554'),
                str(cam.get('main_url', '')).lstrip('/'),  # PATCH-184
                str(cam.get('sub_url', '')).lstrip('/'),
                str(cam.get('sub2_url', '')).lstrip('/'),
                1 if cam.get('enabled', True) else 0,
                cam.get('comment', ''),
                1 if cam.get('audio', True) else 0,
                cam.get('location', '')
            ))"""
    if old in c:
        c = c.replace(old, new, 1);
        n += 1
        print("  [OK] save_cameras_list: INSERT с новыми колонками")

    if n == 3:
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] Сохранено")
            return True
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
    else:
        print(f"  [FAIL] {n}/3 — откат")

    f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
    return False


def patch_stream_manager(f):
    print("--- stream_manager.py ---")
    c = f.read_text(encoding="utf-8")
    n = 0

    old = "            needed[cam.main_route_id] = (cam.main_url, cam.id)"
    new = "            needed[cam.main_route_id] = (cam.build_url('main_url'), cam.id)  # PATCH-184"
    if old in c:
        c = c.replace(old, new, 1);
        n += 1
        print("  [OK] main_url → build_url('main_url')")

    old = "                needed[cam.sub_route_id] = (cam.sub_url, cam.id)"
    new = "                needed[cam.sub_route_id] = (cam.build_url('sub_url'), cam.id)  # PATCH-184"
    if old in c:
        c = c.replace(old, new, 1);
        n += 1
        print("  [OK] sub_url → build_url('sub_url')")

    if n == 2:
        f.write_text(c, encoding="utf-8")
        print("  [OK] Сохранено")
        return True

    print(f"  [FAIL] {n}/2")
    return False


def main():
    root = find_project_root()
    print(f"  [OK] Корень проекта: {root}")
    print()
    print("=" * 76)
    print("184: RTSP URL → части (login/pass/ip/port + main_url/sub_url/sub2_url)")
    print("=" * 76)
    print()

    ok = True
    ok &= migrate_db(root / "data" / "gryphone.db")
    ok &= patch_schema(root / "database" / "sql" / "schema.sql")
    ok &= patch_models(root / "app" / "models.py")
    ok &= patch_database(root / "app" / "database.py")
    ok &= patch_stream_manager(root / "app" / "services" / "stream_manager.py")

    if not ok:
        print()
        print("[FAIL] часть шагов не прошла")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Бэкенд мигрирован!")
    print()
    print("Новая структура камеры:")
    print("  login, pass, ipaddress, port, main_url, sub_url, sub2_url")
    print()
    print("Сборка URL на сервере:")
    print("  rtsp://login:pass@ip:port/main_url")
    print("  (гарантирован один / после порта)")
    print()
    print("ОБЯЗАТЕЛЬНО:")
    print("  1. Перезапустить сервер: python main.py")
    print("  2. Проверить что потоки работают (монитор)")
    print()
    print("Следующий шаг: PATCH-185 (фронтенд CamerasEditor)")
    print("=" * 76)


if __name__ == "__main__":
    main()