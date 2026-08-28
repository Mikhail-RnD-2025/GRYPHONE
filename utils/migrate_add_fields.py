# -*- coding: utf-8 -*-
"""
migrate_add_fields.py — миграция БД для новых полей.

Добавляет поля audio и location в существующие камеры:
  - audio: true (включено по умолчанию)
  - location: "" (пустая строка)

Запуск:  python migrate_add_fields.py
"""
import json
import sqlite3
from pathlib import Path

import sqlite3
from pathlib import Path

# Path to database: parent of utils/ is project root
DB_PATH = Path(__file__).resolve().parent.parent / str(DATABASE_PATH)

print(f"Database path: {DB_PATH}")

if not DB_PATH.exists():
    print(f"ERROR: database not found at {DB_PATH}")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print(f"Database path: {DB_PATH}")

if not DB_PATH.exists():
    print(f"ERROR: database not found at {DB_PATH}")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


def main():
    if not DB_PATH.exists():
        print(f"❌ БД не найдена: {DB_PATH.absolute()}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Получаем текущие камеры
    cursor.execute("SELECT value FROM settings WHERE key = 'cameras'")
    row = cursor.fetchone()
    if not row:
        print("⚠️  В БД нет камер. Миграция не нужна.")
        conn.close()
        return

    cameras = json.loads(row[0])
    print(f"📂 Найдено камер: {len(cameras)}")

    # Добавляем новые поля, если их нет
    added_audio = 0
    added_location = 0
    for cam in cameras:
        if "audio" not in cam:
            cam["audio"] = True
            added_audio += 1
        if "location" not in cam:
            cam["location"] = ""
            added_location += 1

    # Сохраняем обратно
    cursor.execute(
        "UPDATE settings SET value = ? WHERE key = 'cameras'",
        (json.dumps(cameras, ensure_ascii=False),)
    )
    conn.commit()
    conn.close()

    print(f"✅ Добавлено поле 'audio' у {added_audio} камер")
    print(f"✅ Добавлено поле 'location' у {added_location} камер")
    print()
    print("📋 Дальше:")
    print("   python main.py — перезапустить бэкенд")


if __name__ == "__main__":
    main()
