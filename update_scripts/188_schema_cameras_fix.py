#!/usr/bin/env python3
"""
188. update_scripts/188_schema_cameras_fix.py
----------------------------------------------------------------------------
Хирургический фикс schema.sql: полная замена блока CREATE TABLE cameras
на корректный (патч 184v2 оставил мусор).

ЗАПУСК: python update_scripts/188_schema_cameras_fix.py
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


CAMERAS_BLOCK = '''-- ----------------------------------------------------------------------------
-- Таблица: cameras
-- Назначение: Список камер наблюдения с их параметрами.
-- PATCH-188: RTSP URL разбит на части (login/pass/ip/port + пути потоков)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cameras (
    -- Уникальный идентификатор камеры (обычно из Excel или импорта)
    id TEXT PRIMARY KEY,
    -- Человекочитаемое имя камеры
    name TEXT,
    -- PATCH-188: части RTSP URL
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
);

CREATE INDEX IF NOT EXISTS idx_cameras_enabled ON cameras(enabled);
CREATE INDEX IF NOT EXISTS idx_cameras_name ON cameras(name);'''


def main():
    root = find_project_root()
    f = root / "database" / "sql" / "schema.sql"

    print("=" * 76)
    print("188: хирургический фикс schema.sql (блок cameras)")
    print("=" * 76)
    print()

    content = f.read_text(encoding="utf-8")

    # Находим начало блока cameras
    start_markers = [
        "CREATE TABLE IF NOT EXISTS cameras",
        "-- Таблица: cameras",
    ]
    start_idx = None
    for marker in start_markers:
        i = content.find(marker)
        if i != -1:
            start_idx = i
            # откатываемся к началу комментария перед CREATE TABLE
            comment_start = content.rfind("-- ---", 0, i)
            if comment_start != -1 and i - comment_start < 200:
                start_idx = comment_start
            break

    if start_idx is None:
        print("  [FAIL] блок cameras не найден")
        sys.exit(1)

    # Находим конец блока: идём от start_idx, считаем ( и )
    i = content.find("CREATE TABLE IF NOT EXISTS cameras", start_idx)
    paren_depth = 0
    end_idx = None
    in_create = False
    for j in range(i, len(content)):
        ch = content[j]
        if ch == '(':
            paren_depth += 1
            in_create = True
        elif ch == ')':
            paren_depth -= 1
            if in_create and paren_depth == 0:
                # нашли закрывающую )
                # ищем следующий ;
                semi = content.find(";", j)
                if semi == -1:
                    end_idx = j + 1
                else:
                    end_idx = semi + 1
                break

    if end_idx is None:
        print("  [FAIL] не найдено ); в блоке cameras")
        sys.exit(1)

    # Пропускаем последующие CREATE INDEX для cameras (они уже в новом блоке)
    rest = content[end_idx:]
    while True:
        idx_idx = rest.find("CREATE INDEX IF NOT EXISTS idx_cameras_")
        if idx_idx == -1:
            break
        semi = rest.find(";", idx_idx)
        if semi == -1:
            break
        rest = rest[:idx_idx] + rest[semi + 1:]
        end_idx = end_idx + idx_idx + (semi - idx_idx + 1)  # не нужно, но для ясности

    # Убираем старые индексы из rest
    new_rest = ""
    lines = content[end_idx:].split("\n")
    skip_until_non_index = False
    for line in lines:
        if "idx_cameras_" in line:
            continue
        new_rest += line + "\n"
    # убираем лишние пустые строки в начале
    while new_rest.startswith("\n"):
        new_rest = new_rest[1:]

    new_content = content[:start_idx] + CAMERAS_BLOCK + "\n\n" + new_rest

    f.write_text(new_content, encoding="utf-8")
    print("  [OK] Блок cameras заменён полностью")
    print(f"  [OK] Начало: позиция {start_idx}, конец: {end_idx}")

    # Проверяем синтаксис SQLite
    import sqlite3
    try:
        conn = sqlite3.connect(":memory:")
        conn.executescript(new_content)
        cols = conn.execute("PRAGMA table_info(cameras)").fetchall()
        conn.close()
        print(f"  [OK] schema.sql валидна; cameras имеет {len(cols)} колонок:")
        for c in cols:
            print(f"       {c[1]:15} {c[2]}")
    except sqlite3.Error as e:
        print(f"  [FAIL] schema.sql невалидна: {e}")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово!")
    print("  python main.py")
    print()
    print("Сервер должен стартовать, мониторинг — показывать потоки")
    print("=" * 76)


if __name__ == "__main__":
    main()