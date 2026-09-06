#!/usr/bin/env python3
"""
161. update_scripts/161_aspect_ratio_full.py
----------------------------------------------------------------------------
Полная миграция aspect_ratio для таблицы sets:
  1. database/sql/schema.sql — колонка в CREATE TABLE (для новых БД)
  2. app/database.py _create_tables — ALTER TABLE для существующих БД
     (идемпотентно, проверяет PRAGMA table_info)
  3. app/database.py save_sets_data — пишет aspect_ratio
  4. app/database.py get_all_sets — читает aspect_ratio

ЗАПУСК: python update_scripts/161_aspect_ratio_full.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    schema_file = project_root / "database" / "sql" / "schema.sql"
    db_py = project_root / "app" / "database.py"

    print("=" * 76)
    print("161: Полная миграция aspect_ratio (schema + БД + код)")
    print("=" * 76)
    print()

    # ====================================================================
    # 1. SCHEMA.SQL — для новых БД
    # ====================================================================
    print("--- database/sql/schema.sql ---")
    backup_schema = schema_file.with_suffix(".sql.bak-161")
    backup_schema.write_text(schema_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_schema.name}")

    schema = schema_file.read_text(encoding="utf-8")

    if "aspect_ratio" in schema:
        print("  [OK] Колонка уже в схеме")
    else:
        old = """    -- Является ли набором по умолчанию при старте (0=нет, 1=да)
    is_default INTEGER DEFAULT 0
);"""
        new = """    -- Является ли набором по умолчанию при старте (0=нет, 1=да)
    is_default INTEGER DEFAULT 0,
    -- PATCH-161: пропорции ячеек сетки ('16:9' или '4:3')
    aspect_ratio TEXT DEFAULT '16:9'
);"""
        if old in schema:
            schema = schema.replace(old, new, 1)
            schema_file.write_text(schema, encoding="utf-8")
            print("  [OK] CREATE TABLE sets: + aspect_ratio TEXT DEFAULT '16:9'")
        else:
            print("  [FAIL] Блок CREATE TABLE sets не найден")
            sys.exit(1)

    # ====================================================================
    # 2. DATABASE.PY — миграция + чтение/запись
    # ====================================================================
    print()
    print("--- app/database.py ---")
    backup_db = db_py.with_suffix(".py.bak-161")
    backup_db.write_text(db_py.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_db.name}")

    content = db_py.read_text(encoding="utf-8")

    if "PATCH-161" in content:
        print("  [OK] Уже применён")
    else:
        n = 0

        # 2a. Миграция в _create_tables (после executescript)
        old = "            conn.executescript(schema_sql)"
        new = """            conn.executescript(schema_sql)

            # PATCH-161: миграция существующих БД — добавляем aspect_ratio
            # (идемпотентно: CREATE TABLE IF NOT EXISTS не меняет старые БД)
            mig_cursor = conn.cursor()
            mig_cursor.execute("PRAGMA table_info(sets)")
            _cols = [r[1] for r in mig_cursor.fetchall()]
            if "aspect_ratio" not in _cols:
                mig_cursor.execute(
                    "ALTER TABLE sets ADD COLUMN aspect_ratio TEXT DEFAULT '16:9'"
                )
                conn.commit()
                print("[PATCH-161] Миграция: sets + aspect_ratio")"""
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] _create_tables: авто-миграция ALTER TABLE")
        else:
            print("  [WARN] executescript не найден — миграцию добавьте вручную")

        # 2b. save_sets_data: пишем aspect_ratio
        old = """            cursor.execute(\"\"\"
                INSERT OR REPLACE INTO sets
                (id, name, grid_columns, grid_rows, is_default)
                VALUES (?, ?, ?, ?, ?)
            \"\"\", (
                set_id,
                set_info.get('name', set_id),
                set_info.get('max_columns', set_info.get('grid_columns', 4)),
                set_info.get('max_rows', set_info.get('grid_rows', 3)),
                is_default
            ))"""
        new = """            cursor.execute(\"\"\"
                INSERT OR REPLACE INTO sets
                (id, name, grid_columns, grid_rows, is_default, aspect_ratio)
                VALUES (?, ?, ?, ?, ?, ?)
            \"\"\", (
                set_id,
                set_info.get('name', set_id),
                set_info.get('max_columns', set_info.get('grid_columns', 4)),
                set_info.get('max_rows', set_info.get('grid_rows', 3)),
                is_default,
                set_info.get('aspect_ratio', '16:9')  # PATCH-161
            ))"""
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] save_sets_data: пишет aspect_ratio")
        else:
            print("  [WARN] INSERT в save_sets_data не найден")

        # 2c. get_all_sets: читаем aspect_ratio
        old = '        cursor.execute("SELECT id, name, grid_columns, grid_rows, is_default FROM sets")'
        new = '        cursor.execute("SELECT id, name, grid_columns, grid_rows, is_default, aspect_ratio FROM sets")  # PATCH-161'
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] get_all_sets: SELECT + aspect_ratio")
        else:
            print("  [WARN] SELECT в get_all_sets не найден")

        old = """            sets_data[set_id] = {
                'name': row[1],
                'grid_columns': row[2],
                'grid_rows': row[3],
                'cameras': []
            }"""
        new = """            sets_data[set_id] = {
                'name': row[1],
                'grid_columns': row[2],
                'grid_rows': row[3],
                'aspect_ratio': (row[5] or '16:9') if len(row) > 5 else '16:9',  # PATCH-161
                'cameras': []
            }"""
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] get_all_sets: dict + aspect_ratio")
        else:
            print("  [WARN] dict в get_all_sets не найден")

        if n < 3:
            print(f"  [FAIL] Заменено только {n}/4 — откат")
            db_py.write_text(backup_db.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        try:
            compile(content, str(db_py), "exec")
        except SyntaxError as e:
            print(f"  [FAIL] Синтаксис: {e} — откат")
            db_py.write_text(backup_db.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        db_py.write_text(content, encoding="utf-8")
        print("  [OK] Сохранено")

    print()
    print("=" * 76)
    print("✅ Полная миграция готова!")
    print()
    print("Теперь aspect_ratio хранится:")
    print("  • schema.sql        → новые БД создаются с колонкой")
    print("  • живая БД          → ALTER TABLE при старте сервера")
    print("  • save_sets_data    → пишется при сохранении")
    print("  • get_all_sets      → читается при загрузке")
    print()
    print("Перезапустите сервер:")
    print("  python main.py")
    print("  (в логе будет: [PATCH-161] Миграция: sets + aspect_ratio)")
    print()
    print("Проверка БД:")
    print("  sqlite3 database/gryphone-vision.db 'SELECT id, name, aspect_ratio FROM sets'")
    print("=" * 76)


if __name__ == "__main__":
    main()