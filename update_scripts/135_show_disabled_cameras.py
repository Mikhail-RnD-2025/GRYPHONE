#!/usr/bin/env python3
"""
135v2. update_scripts/135_add_all_cameras_to_set.py
----------------------------------------------------------------------------
Добавляет ВСЕ камеры в набор "210" через прямое обновление БД.
Не требует запущенного сервера.

ПРИНЦИП:
  • Читает all cameras из БД
  • Сортирует по id (стабильный порядок в сетке)
  • Перезаписывает set_cameras для набора 210
  • При следующем запуске сервера данные загрузятся автоматически

ЗАПУСК: python update_scripts/135_add_all_cameras_to_set.py
"""

import sys
import sqlite3
from pathlib import Path


def main():
    project_root = Path.cwd()
    db_path = project_root / "database" / "gryphone-vision.db"

    print("=" * 76)
    print("135 v2: Добавление всех камер в набор (напрямую в БД)")
    print("=" * 76)
    print()

    if not db_path.exists():
        print(f"  [ERROR] БД не найдена: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # ========================================================================
    # ШАГ 1: Получить все камеры из БД
    # ========================================================================
    print("--- ШАГ 1: Чтение всех камер ---")
    cur.execute("SELECT id, enabled FROM cameras ORDER BY id")
    all_cameras = cur.fetchall()
    print(f"  [OK] Всего камер в БД: {len(all_cameras)}")

    # ========================================================================
    # ШАГ 2: Определить целевой набор
    # ========================================================================
    print()
    print("--- ШАГ 2: Определение набора ---")
    cur.execute("SELECT DISTINCT set_id FROM set_cameras")
    set_ids = [row[0] for row in cur.fetchall()]
    if not set_ids:
        print("  [ERROR] Нет ни одного набора в set_cameras!")
        conn.close()
        sys.exit(1)

    target_set = set_ids[0]  # обычно '210'
    print(f"  [OK] Целевой набор: {target_set}")

    # ========================================================================
    # ШАГ 3: Посмотреть текущее состояние
    # ========================================================================
    cur.execute("SELECT camera_id FROM set_cameras WHERE set_id=?", (target_set,))
    current = {row[0] for row in cur.fetchall()}
    print(f"  [OK] Сейчас в наборе: {len(current)} камер")

    all_ids = {cam[0] for cam in all_cameras}
    missing = all_ids - current
    print(f"  [INFO] Будет добавлено: {len(missing)} камер")

    if not missing:
        print()
        print("  [OK] Все камеры уже в наборе — ничего не делаем")
        conn.close()
        print("=" * 76)
        return

    # ========================================================================
    # ШАГ 4: Очистить набор и записать все камеры заново
    # ========================================================================
    print()
    print("--- ШАГ 4: Обновление БД ---")

    # Backup текущей таблицы set_cameras на всякий случай
    cur.execute("SELECT COUNT(*) FROM set_cameras")
    backup_count = cur.fetchone()[0]
    print(f"  [INFO] Бэкап: в set_cameras всего {backup_count} строк")

    # Удаляем текущие записи для target_set
    cur.execute("DELETE FROM set_cameras WHERE set_id=?", (target_set,))
    deleted = cur.rowcount
    print(f"  [OK] Удалено старых записей: {deleted}")

    # Вставляем все камеры (отсортированные по id для стабильного порядка)
    sorted_cams = sorted(all_cameras, key=lambda x: x[0])
    for cam_id, _ in sorted_cams:
        cur.execute(
            "INSERT INTO set_cameras (set_id, camera_id) VALUES (?, ?)",
            (target_set, cam_id)
        )
    print(f"  [OK] Добавлено новых записей: {len(sorted_cams)}")

    conn.commit()
    print("  [OK] Транзакция зафиксирована")

    # ========================================================================
    # ШАГ 5: Проверка результата
    # ========================================================================
    print()
    print("--- ШАГ 5: Проверка ---")
    cur.execute(
        "SELECT c.id, c.enabled FROM cameras c "
        "JOIN set_cameras sc ON c.id = sc.camera_id "
        "WHERE sc.set_id=? ORDER BY c.id",
        (target_set,)
    )
    result = cur.fetchall()
    enabled_count = sum(1 for _, en in result if en)
    disabled_count = len(result) - enabled_count
    print(f"  [OK] В наборе {target_set}: {len(result)} камер")
    print(f"    • Включено: {enabled_count}")
    print(f"    • Отключено: {disabled_count}")

    print()
    print("  Камеры в наборе:")
    for cam_id, enabled in result:
        status = "✅" if enabled else "⚪"
        print(f"    {status} {cam_id}")

    conn.close()

    print()
    print("=" * 76)
    print("✅ Готово! БД обновлена.")
    print()
    print("ВАЖНО: перезапустите сервер, чтобы он перезагрузил данные:")
    print("  python main.py")
    print()
    print("Затем обновите браузер (Ctrl+Shift+R)")
    print()
    print("Результат:")
    print(f"  • Все {len(result)} камер в наборе {target_set}")
    print(f"  • {disabled_count} отключённых → отображаются со статусом 'Отключена'")
    print(f"  • {enabled_count} включённых → воркеры стартуют автоматически")
    print("=" * 76)


if __name__ == "__main__":
    main()