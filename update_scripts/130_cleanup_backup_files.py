#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
130. update_scripts/130_cleanup_backup_files.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Удаляет все .bak-* файлы и временные артефакты из проекта.

ЧТО УДАЛЯЕТ:
  • Все файлы *.bak-* (бэкапы от предыдущих патчей)
  • Папку .css_chunks/ (временные чанки CSS)
  • Файл .unused_classes.txt (временный файл анализа)

ЧТО НЕ УДАЛЯЕТ:
  • Исходные файлы (.py, .jsx, .css)
  • Папку node_modules/
  • Папку .git/
  • Папку __pycache__/ (опционально, см. CLEANUP_PYCACHE)

ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
ЗАПУСК: python update_scripts/130_cleanup_backup_files.py
============================================================================
"""

import os
import shutil
import sys
from pathlib import Path

# Конфигурация
CLEANUP_PYCACHE = False  # Установите True, если нужно удалить __pycache__
DRY_RUN = False  # Установите True для тестового запуска (без удаления)


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("130: Очистка мусора из проекта")
    print(f"Корень проекта: {project_root}")
    print(f"Режим: {'ТЕСТОВЫЙ (без удаления)' if DRY_RUN else 'РАБОЧИЙ'}")
    print("=" * 76)
    print()

    # Паттерны для поиска
    patterns_to_delete = [
        ("*.bak-*", "Бэкапы файлов"),
        (".unused_classes.txt", "Временные файлы анализа"),
    ]

    folders_to_delete = [
        ".css_chunks",
    ]

    if CLEANUP_PYCACHE:
        folders_to_delete.append("__pycache__")

    # Директории для пропуска
    skip_dirs = {
        'node_modules', '.git', 'dist', '.venv', 'venv',
        'env', '.env', '.idea', '.vscode'
    }

    stats = {
        'files_deleted': 0,
        'files_bytes': 0,
        'folders_deleted': 0,
        'errors': []
    }

    # ========================================================================
    # ШАГ 1: Поиск и удаление файлов по паттернам
    # ========================================================================
    print("--- ШАГ 1: Поиск файлов для удаления ---")

    files_to_delete = []

    for pattern, description in patterns_to_delete:
        print(f"\n  Поиск: {description} ({pattern})")
        count = 0

        for root, dirs, files in os.walk(project_root):
            # Пропускаем служебные директории
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for filename in files:
                if filename.endswith('.bak-') or '.bak-' in filename:
                    filepath = Path(root) / filename
                    files_to_delete.append(filepath)
                    count += 1
                    print(f"    [FOUND] {filepath.relative_to(project_root)}")

                elif filename == '.unused_classes.txt':
                    filepath = Path(root) / filename
                    files_to_delete.append(filepath)
                    count += 1
                    print(f"    [FOUND] {filepath.relative_to(project_root)}")

        if count == 0:
            print(f"    [OK] Не найдено")
        else:
            print(f"    Найдено файлов: {count}")

    print()

    # ========================================================================
    # ШАГ 2: Поиск папок для удаления
    # ========================================================================
    print("--- ШАГ 2: Поиск папок для удаления ---")

    folders_found = []

    for folder_name in folders_to_delete:
        print(f"\n  Поиск папки: {folder_name}")
        count = 0

        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            if folder_name in dirs:
                folder_path = Path(root) / folder_name
                folders_found.append(folder_path)
                count += 1
                print(f"    [FOUND] {folder_path.relative_to(project_root)}")

        if count == 0:
            print(f"    [OK] Не найдено")

    print()

    # ========================================================================
    # ШАГ 3: Удаление
    # ========================================================================
    print("--- ШАГ 3: Удаление ---")

    # Удаление файлов
    if files_to_delete:
        print(f"\n  Удаляю файлов: {len(files_to_delete)}")
        for filepath in files_to_delete:
            try:
                size = filepath.stat().st_size
                if not DRY_RUN:
                    filepath.unlink()
                stats['files_deleted'] += 1
                stats['files_bytes'] += size
                print(f"    [DEL] {filepath.relative_to(project_root)} ({size} байт)")
            except Exception as e:
                stats['errors'].append(f"{filepath}: {e}")
                print(f"    [ERROR] {filepath.relative_to(project_root)}: {e}")
    else:
        print("\n  Файлов для удаления не найдено")

    # Удаление папок
    if folders_found:
        print(f"\n  Удаляю папок: {len(folders_found)}")
        for folder_path in folders_found:
            try:
                # Подсчёт размера папки
                folder_size = sum(
                    f.stat().st_size
                    for f in folder_path.rglob('*')
                    if f.is_file()
                )
                if not DRY_RUN:
                    shutil.rmtree(folder_path)
                stats['folders_deleted'] += 1
                stats['files_bytes'] += folder_size
                print(f"    [DEL] {folder_path.relative_to(project_root)} ({folder_size} байт)")
            except Exception as e:
                stats['errors'].append(f"{folder_path}: {e}")
                print(f"    [ERROR] {folder_path.relative_to(project_root)}: {e}")
    else:
        print("\n  Папок для удаления не найдено")

    print()

    # ========================================================================
    # ИТОГ
    # ========================================================================
    print("=" * 76)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 76)
    print(f"  Файлов удалено: {stats['files_deleted']}")
    print(f"  Папок удалено: {stats['folders_deleted']}")
    print(f"  Освобождено места: {stats['files_bytes']:,} байт ({stats['files_bytes'] / 1024:.2f} KB)")

    if stats['errors']:
        print(f"\n  ⚠️ Ошибок: {len(stats['errors'])}")
        for error in stats['errors'][:5]:  # Показываем первые 5
            print(f"    • {error}")
        if len(stats['errors']) > 5:
            print(f"    ... и ещё {len(stats['errors']) - 5}")

    print()

    if DRY_RUN:
        print("⚠️ ТЕСТОВЫЙ РЕЖИМ: файлы не были удалены")
        print("   Для реального удаления измените DRY_RUN = False в начале скрипта")
    else:
        print("✅ Очистка завершена успешно")

    print("=" * 76)

    # Код возврата
    if stats['errors']:
        sys.exit(1)


if __name__ == "__main__":
    main()