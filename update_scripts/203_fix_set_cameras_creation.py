#!/usr/bin/env python3
"""
203.1 update_scripts/203_fix_set_cameras_creation.py
----------------------------------------------------------------------------
Фикс миграции: создаёт set_cameras если её нет + добавляет position.
Также обновляет schema.sql для будущих новых БД.

ЗАПУСК: python update_scripts/203_fix_set_cameras_creation.py
"""

import sys
import sqlite3
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


def migrate_db(db_path):
    print("--- миграция БД: set_cameras ---")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Проверяем наличие таблицы
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='set_cameras'")
    if not cur.fetchone():
        print("  [WARN] таблица set_cameras не найдена — создаю")
        cur.execute("""
            CREATE TABLE set_cameras (
                set_id TEXT,
                camera_id TEXT,
                position INTEGER DEFAULT 0,
                PRIMARY KEY (set_id, camera_id),
                FOREIGN KEY (set_id) REFERENCES sets(id) ON DELETE CASCADE,
                FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_set_cameras_set_id ON set_cameras(set_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_set_cameras_camera_id ON set_cameras(camera_id)")
        print("  [OK] set_cameras создана с колонкой position")
    else:
        # Таблица есть — проверяем колонку position
        cols = [r[1] for r in cur.execute("PRAGMA table_info(set_cameras)")]
        if "position" not in cols:
            print("  [WARN] колонка position не найдена — добавляю")
            cur.execute("ALTER TABLE set_cameras ADD COLUMN position INTEGER DEFAULT 0")
            cur.execute("UPDATE set_cameras SET position = rowid")
            print("  [OK] position добавлена + заполнена из rowid")
        else:
            print("  [OK] set_cameras с position уже есть")

    conn.commit()
    conn.close()
    return True


def update_schema_sql(f):
    print("--- database/sql/schema.sql: set_cameras с position ---")
    c = f.read_text(encoding="utf-8")

    old = """CREATE TABLE IF NOT EXISTS set_cameras (
    -- Ссылка на набор (sets.id)
    set_id TEXT,
    -- Ссылка на камеру (cameras.id)
    camera_id TEXT,
    -- Составной первичный ключ: камера может быть в наборе только один раз
    PRIMARY KEY (set_id, camera_id),
    -- Внешний ключ на таблицу sets (каскадное удаление)
    FOREIGN KEY (set_id) REFERENCES sets(id) ON DELETE CASCADE,
    -- Внешний ключ на таблицу cameras (каскадное удаление)
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
);"""

    new = """CREATE TABLE IF NOT EXISTS set_cameras (
    -- Ссылка на набор (sets.id)
    set_id TEXT,
    -- Ссылка на камеру (cameras.id)
    camera_id TEXT,
    -- PATCH-203: порядок камер в наборе
    position INTEGER DEFAULT 0,
    -- Составной первичный ключ: камера может быть в наборе только один раз
    PRIMARY KEY (set_id, camera_id),
    -- Внешний ключ на таблицу sets (каскадное удаление)
    FOREIGN KEY (set_id) REFERENCES sets(id) ON DELETE CASCADE,
    -- Внешний ключ на таблицу cameras (каскадное удаление)
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
);"""

    if old in c:
        c = c.replace(old, new, 1)
        f.write_text(c, encoding="utf-8")
        print("  [OK] schema.sql: set_cameras.position добавлена")
        return True
    elif "position INTEGER DEFAULT 0" in c:
        print("  [OK] schema.sql уже содержит position")
        return True
    else:
        print("  [FAIL] set_cameras не найден в schema.sql")
        return False


def main():
    root = find_project_root()
    db_path = root / "database" / "gryphone-vision.db"

    print("=" * 76)
    print("203.1: фикс миграции set_cameras")
    print("=" * 76)
    print()

    ok = True
    ok &= migrate_db(str(db_path))
    ok &= update_schema_sql(root / "database" / "sql" / "schema.sql")

    if not ok:
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Повторите PATCH-203:")
    print("  python update_scripts/203_set_repository_full.py")
    print("=" * 76)


if __name__ == "__main__":
    main()