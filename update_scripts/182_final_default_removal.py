#!/usr/bin/env python3
"""
182. update_scripts/182_final_default_removal.py
----------------------------------------------------------------------------
ФИНАЛЬНАЯ версия ветки "выбор набора" (заменяет 177/180/181):
  1. schema.sql: колонка is_default + индекс удалены
  2. живая БД: DROP INDEX + DROP COLUMN через Python (sqlite3 CLI не нужен)
  3. database.py: INSERT/SELECT без is_default, без default_set
  4. camera_service.py: убран _default_set; сервер НЕ помнит выбор ('')
  5. api.py: GET /api/sets → current_set
  6. Header.jsx: localStorage['gryphone_current_set'] + sync сервера

ЗАПУСК: python update_scripts/182_final_default_removal.py
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


def migrate_db(db_file):
    print("--- живая БД ---")
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(sets)")
    cols = [r[1] for r in cur.fetchall()]
    if "is_default" not in cols:
        print("  [OK] колонки is_default уже нет")
        conn.close()
        return True
    cur.execute("DROP INDEX IF EXISTS idx_sets_is_default")
    print("  [OK] индекс удалён")
    try:
        cur.execute("ALTER TABLE sets DROP COLUMN is_default")
        conn.commit()
        print("  [OK] DROP COLUMN is_default")
    except sqlite3.OperationalError as e:
        print(f"  [WARN] {e} — пересборка таблицы")
        cur.executescript("""
            CREATE TABLE sets_new (
                id TEXT PRIMARY KEY,
                name TEXT,
                grid_columns INTEGER DEFAULT 4,
                grid_rows INTEGER DEFAULT 3,
                aspect_ratio TEXT NOT NULL DEFAULT '16:9'
            );
            INSERT INTO sets_new (id, name, grid_columns, grid_rows, aspect_ratio)
                SELECT id, name, grid_columns, grid_rows, aspect_ratio FROM sets;
            DROP TABLE sets;
            ALTER TABLE sets_new RENAME TO sets;
        """)
        conn.commit()
        print("  [OK] таблица пересобрана")
    conn.close()
    return True


def patch_schema(f):
    print("--- schema.sql ---")
    lines = f.read_text(encoding="utf-8").split("\n")
    out, n = [], 0
    for line in lines:
        if "is_default INTEGER DEFAULT" in line:
            n += 1; continue
        if "idx_sets_is_default" in line:
            n += 1; continue
        if "-- INSERT OR IGNORE INTO sets (id, name, grid_columns, grid_rows, is_default)" in line:
            out.append("-- INSERT OR IGNORE INTO sets (id, name, grid_columns, grid_rows, aspect_ratio)")
            n += 1; continue
        if "-- VALUES ('default', 'По умолчанию', 4, 3, 1);" in line:
            out.append("-- VALUES ('default', 'По умолчанию', 4, 3, '16:9');")
            n += 1; continue
        out.append(line)
    if n >= 2:
        f.write_text("\n".join(out), encoding="utf-8")
        print(f"  [OK] удалено {n} вхождений")
        return True
    print("  [FAIL] schema.sql не изменена")
    return False


def patch_database(f):
    print("--- database.py ---")
    b = f.with_suffix(".py.bak-182")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    old = """                default_set = sets_data.get("default_set", "")
                sets_dict = sets_data.get("sets", {})
                for set_id, set_info in sets_dict.items():
                    is_default = 1 if set_id == default_set else 0
                    cursor.execute(\"\"\"
                        INSERT OR REPLACE INTO sets
                        (id, name, grid_columns, grid_rows, is_default)
                        VALUES (?, ?, ?, ?, ?)
                    \"\"\", (
                        set_id,
                        set_info.get("name", set_id),
                        set_info.get("max_columns", set_info.get("grid_columns", 4)),
                        set_info.get("max_rows", set_info.get("grid_rows", 3)),
                        is_default
                    ))"""
    new = """                sets_dict = sets_data.get("sets", {})
                for set_id, set_info in sets_dict.items():
                    cursor.execute(\"\"\"
                        INSERT OR REPLACE INTO sets
                        (id, name, grid_columns, grid_rows, aspect_ratio)
                        VALUES (?, ?, ?, ?, ?)
                    \"\"\", (
                        set_id,
                        set_info.get("name", set_id),
                        set_info.get("max_columns", set_info.get("grid_columns", 4)),
                        set_info.get("max_rows", set_info.get("grid_rows", 3)),
                        set_info.get("aspect_ratio", "16:9")
                    ))"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] _populate: INSERT без is_default")

    old = """            cursor.execute("SELECT id FROM sets WHERE is_default = 1 LIMIT 1")
            default_set_row = cursor.fetchone()
            if not default_set_row:
                # Если нет набора по умолчанию, берём первый
                cursor.execute("SELECT id FROM sets LIMIT 1")
                default_set_row = cursor.fetchone()"""
    new = """            # PATCH-182: набора по умолчанию нет — берём первый
            cursor.execute("SELECT id FROM sets LIMIT 1")
            default_set_row = cursor.fetchone()"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] авто-привязка: первый набор")

    old = """        cursor.execute("SELECT id, name, grid_columns, grid_rows, is_default, aspect_ratio FROM sets")  # PATCH-161
        sets_rows = cursor.fetchall()

        sets_data = {}
        default_set = None

        for row in sets_rows:
            set_id = row[0]
            sets_data[set_id] = {
                'name': row[1],
                'grid_columns': row[2],
                'grid_rows': row[3],
                'aspect_ratio': (row[5] or '16:9') if len(row) > 5 else '16:9',  # PATCH-161
                'cameras': []
            }
            if row[4]:
                default_set = set_id"""
    new = """        cursor.execute("SELECT id, name, grid_columns, grid_rows, aspect_ratio FROM sets")  # PATCH-182
        sets_rows = cursor.fetchall()

        sets_data = {}

        for row in sets_rows:
            set_id = row[0]
            sets_data[set_id] = {
                'name': row[1],
                'grid_columns': row[2],
                'grid_rows': row[3],
                'aspect_ratio': (row[4] or '16:9') if len(row) > 4 else '16:9',  # PATCH-182
                'cameras': []
            }"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] get_all_sets: SELECT без is_default")

    old = """        return {
            'default_set': default_set or '',
            'sets': sets_data
        }"""
    new = """        return {
            'sets': sets_data
        }"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] get_all_sets: без default_set")

    old = """        default_set = sets_data.get('default_set', '')
        sets_dict = sets_data.get('sets', {})
        cursor.execute("DELETE FROM set_cameras")
        cursor.execute("DELETE FROM sets")
        for set_id, set_info in sets_dict.items():
            if not isinstance(set_info, dict):
                continue
            is_default = 1 if set_id == default_set else 0
            cursor.execute(\"\"\"
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
    new = """        sets_dict = sets_data.get('sets', {})
        cursor.execute("DELETE FROM set_cameras")
        cursor.execute("DELETE FROM sets")
        for set_id, set_info in sets_dict.items():
            if not isinstance(set_info, dict):
                continue
            cursor.execute(\"\"\"
                INSERT OR REPLACE INTO sets
                (id, name, grid_columns, grid_rows, aspect_ratio)
                VALUES (?, ?, ?, ?, ?)
            \"\"\", (
                set_id,
                set_info.get('name', set_id),
                set_info.get('max_columns', set_info.get('grid_columns', 4)),
                set_info.get('max_rows', set_info.get('grid_rows', 3)),
                set_info.get('aspect_ratio', '16:9')
            ))"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] save_sets_data: INSERT без is_default")

    if n == 5:
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] Сохранено")
            return True
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
    else:
        print(f"  [FAIL] {n}/5 — откат")
    f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
    return False


def patch_service(f):
    print("--- camera_service.py ---")
    b = f.with_suffix(".py.bak-182")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    old = """        self._default_set: str = ""
        self._current_set: str = """""
    new = """        self._current_set: str = """""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] __init__: без _default_set")

    old = """        self._default_set = (
            raw_sets.get("default_set", "") if isinstance(raw_sets, dict) else ""
        )
        if not self._default_set or self._default_set not in self._sets:
            self._default_set = next(iter(self._sets), "")
        self._current_set = self._default_set"""
    new = """        # PATCH-182: сервер НЕ хранит выбор — клиент (localStorage) синхронизирует
        self._current_set = """""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] _load: current = ''")

    old = """    def default_set_id(self) -> str:
        return self._default_set

"""
    if old in c:
        c = c.replace(old, "", 1); n += 1
        print("  [OK] default_set_id удалён")

    old = """        self._default_set = raw.get("default_set", "") or self._default_set
        if self._current_set not in self._sets:
            self._current_set = self._default_set"""
    new = """        if self._current_set not in self._sets:
            self._current_set = """""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] save_sets: без default_set")

    if n == 4:
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] Сохранено")
            return True
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
    else:
        print(f"  [FAIL] {n}/4 — откат")
    f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
    return False


def patch_api(f):
    print("--- api.py ---")
    c = f.read_text(encoding="utf-8")
    old = '        "default_set": camera_service.default_set_id(),'
    new = '        "current_set": camera_service.current_set_id(),  # PATCH-182'
    if old in c:
        f.write_text(c.replace(old, new, 1), encoding="utf-8")
        print("  [OK] GET /api/sets: current_set")
        return True
    print("  [WARN] якорь не найден")
    return False


def patch_header(f):
    print("--- Header.jsx ---")
    b = f.with_suffix(".jsx.bak-182")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    m = 0

    old = "      setCurrentSet('')  // PATCH-178"
    new = """      // PATCH-182: последний выбор хранится ЛОКАЛЬНО в браузере
      const stored = localStorage.getItem('gryphone_current_set') || ''
      if (stored && data.sets && data.sets[stored]) {
        setCurrentSet(stored)
        switchSet(stored).catch(() => {})  // синхронизируем сервер
      } else {
        setCurrentSet('')
      }"""
    if old in c:
        c = c.replace(old, new, 1); m += 1
        print("  [OK] loadSets: localStorage")

    old = """  const handleSetChange = async (setId) => {
    setCurrentSet(setId)
"""
    new = """  const handleSetChange = async (setId) => {
    setCurrentSet(setId)
    localStorage.setItem('gryphone_current_set', setId)  // PATCH-182
"""
    if old in c:
        c = c.replace(old, new, 1); m += 1
        print("  [OK] handleSetChange: запись в localStorage")

    if m == 2 and c.count('{') == c.count('}'):
        f.write_text(c, encoding="utf-8")
        print("  [OK] Сохранено")
        return True
    print(f"  [FAIL] {m}/2 — откат")
    f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
    return False


def main():
    root = find_project_root()
    print(f"  [OK] Корень проекта: {root}")
    print()
    print("=" * 76)
    print("182: ФИНАЛЬНОЕ удаление default + localStorage-выбор")
    print("=" * 76)
    print()

    ok = True
    ok &= migrate_db(root / "data" / "gryphone.db")
    ok &= patch_schema(root / "database" / "sql" / "schema.sql")
    ok &= patch_database(root / "app" / "database.py")
    ok &= patch_service(root / "app" / "services" / "camera_service.py")
    ok &= patch_api(root / "app" / "routes" / "api.py")
    ok &= patch_header(root / "frontend" / "src" / "components" / "Header.jsx")

    if not ok:
        print()
        print("[FAIL] часть шагов не прошла — см. вывод выше")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово!")
    print()
    print("ОБЯЗАТЕЛЬНО:")
    print("  1. Перезапустить сервер: python main.py")
    print(f"  2. cd {root}/frontend && npm run build")
    print("  3. Ctrl+Shift+R")
    print()
    print("Поведение:")
    print("  • Первый заход в браузере → «— выберите набор —»")
    print("  • Выбрали набор → localStorage помнит → при возврате имя в селекторе")
    print("  • Сервер ничего не хранит; синхронизация через switchSet")
    print("  • is_default полностью удалён из схемы, БД и кода")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "refactor: remove is_default/default_set + localStorage set choice (PATCH-182)" \\')
    print('  -m "schema+DB: DROP COLUMN is_default, DROP INDEX (via python sqlite3)" \\')
    print('  -m "database.py/camera_service/api: default_set concept removed" \\')
    print('  -m "Header: last set stored in localStorage, server synced via switchSet" \\')
    print('  -m "supersedes PATCH-177/180/181"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()