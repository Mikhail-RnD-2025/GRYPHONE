#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
116. update_scripts/116_final_css_cleanup.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Финальная очистка CSS от мусора:
  1. Удаляет все .bak файлы из папки styles/
  2. Удаляет дубликаты в layout.css
  3. Удаляет дубликаты в camera.css
  4. Исправляет некорректные комментарии
  5. Проверяет использование классов в JSX

ЗАПУСК: python update_scripts/116_final_css_cleanup.py
============================================================================
"""

import sys
import re
from pathlib import Path


def main():
    project_root = Path.cwd()
    styles_dir = project_root / "frontend/src/styles"

    print("=" * 76)
    print("116: Финальная очистка CSS")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # ========================================================================
    # ШАГ 1: Удаление .bak файлов
    # ========================================================================
    print("--- ШАГ 1: Удаление .bak файлов ---")
    bak_files = list(styles_dir.glob("*.bak-*"))

    if bak_files:
        for bak_file in bak_files:
            bak_file.unlink()
            print(f"  [DEL] {bak_file.name}")
        print(f"  Удалено файлов: {len(bak_files)}")
    else:
        print("  [OK] .bak файлов не найдено")
    print()

    # ========================================================================
    # ШАГ 2: Очистка layout.css (удаление дубликатов)
    # ========================================================================
    print("--- ШАГ 2: Очистка layout.css ---")
    layout_css = styles_dir / "layout.css"

    if layout_css.exists():
        content = layout_css.read_text(encoding="utf-8")
        original_size = len(content)

        # Удаляем первый дубликат .page.monitor-page (строки 15-18)
        # Оставляем второй, более полный блок (строки 21-25)
        old_duplicate = """.page.monitor-page,
.monitor-page {
  padding-top: 0 !important;
}

"""

        if old_duplicate in content:
            content = content.replace(old_duplicate, "")
            print("  [FIX] Удалён дубликат .page.monitor-page")
        else:
            print("  [OK] Дубликат не найден (уже удалён)")

        new_size = len(content)
        saved = original_size - new_size
        print(f"  Экономия: {saved} байт")

        layout_css.write_text(content, encoding="utf-8")
    else:
        print("  [WARN] layout.css не найден")
    print()

    # ========================================================================
    # ШАГ 3: Очистка camera.css (удаление дубликатов)
    # ========================================================================
    print("--- ШАГ 3: Очистка camera.css ---")
    camera_css = styles_dir / "camera.css"

    if camera_css.exists():
        content = camera_css.read_text(encoding="utf-8")
        original_size = len(content)

        # Удаляем первый блок .camera-video (оставляем более специфичный .fullscreen-grid .camera-card video)
        old_duplicate = """.camera-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
  z-index: 1;
}

"""

        if old_duplicate in content:
            content = content.replace(old_duplicate, "")
            print("  [FIX] Удалён дубликат .camera-video")
        else:
            print("  [OK] Дубликат не найден (уже удалён)")

        new_size = len(content)
        saved = original_size - new_size
        print(f"  Экономия: {saved} байт")

        camera_css.write_text(content, encoding="utf-8")
    else:
        print("  [WARN] camera.css не найден")
    print()

    # ========================================================================
    # ШАГ 4: Исправление комментариев в header.css
    # ========================================================================
    print("--- ШАГ 4: Исправление комментариев header.css ---")
    header_css = styles_dir / "header.css"

    if header_css.exists():
        content = header_css.read_text(encoding="utf-8")

        old_comment = """/* ============================================================
   Шапка приложения — ПОЧТИ ПРОЗРАЧНАЯ
   (фон едва заметен, элементы чётко видимы)
   ============================================================ */"""

        new_comment = """/* ============================================================
   Шапка приложения — ПОЛУПРОЗРАЧНЫЙ ГРАДИЕНТ
   (0.5 → 0.4 → 0.2 с размытием blur(8px))
   ============================================================ */"""

        if old_comment in content:
            content = content.replace(old_comment, new_comment)
            header_css.write_text(content, encoding="utf-8")
            print("  [FIX] Комментарий обновлён")
        else:
            print("  [OK] Комментарий уже корректен")
    else:
        print("  [WARN] header.css не найден")
    print()

    # ========================================================================
    # ШАГ 5: Проверка использования классов
    # ========================================================================
    print("--- ШАГ 5: Проверка использования классов ---")

    # Классы для проверки
    classes_to_check = [
        'placeholder-card', 'placeholder-icon',
        'tabs', 'tab-content',
        'empty-state'
    ]

    # Ищем в JSX файлах
    pages_dir = project_root / "frontend/src/pages"
    components_dir = project_root / "frontend/src/components"

    jsx_files = list(pages_dir.glob("*.jsx")) + list(components_dir.glob("*.jsx"))

    print(f"  Проверяю {len(classes_to_check)} классов в {len(jsx_files)} JSX файлах")
    print()

    for cls in classes_to_check:
        found_in = []
        for jsx_file in jsx_files:
            content = jsx_file.read_text(encoding="utf-8")
            if cls in content:
                found_in.append(jsx_file.name)

        if found_in:
            print(f"  [USED] .{cls}: найден в {len(found_in)} файлах")
            for fname in found_in[:3]:  # Показываем максимум 3 файла
                print(f"          • {fname}")
            if len(found_in) > 3:
                print(f"          • ... и ещё {len(found_in) - 3}")
        else:
            print(f"  [UNUSED] .{cls}: НЕ используется")
    print()

    # ========================================================================
    # ШАГ 6: Итоговая статистика
    # ========================================================================
    print("--- ШАГ 6: Итоговая статистика ---")

    css_files = list(styles_dir.glob("*.css"))
    total_size = sum(f.stat().st_size for f in css_files)

    print(f"  CSS файлов: {len(css_files)}")
    for css_file in sorted(css_files):
        size = css_file.stat().st_size
        print(f"    • {css_file.name}: {size} байт")

    print(f"\n  Общий размер: {total_size} байт ({total_size / 1024:.2f} KB)")
    print()

    # ========================================================================
    # ИТОГ
    # ========================================================================
    print("=" * 76)
    print("Готово! Финальная очистка завершена.")
    print()
    print("Что сделано:")
    print("  • Удалены все .bak файлы из папки styles/")
    print("  • Удалены дубликаты в layout.css и camera.css")
    print("  • Исправлены некорректные комментарии")
    print("  • Проверено использование классов")
    print()
    print("Рекомендации:")
    print("  • Если .placeholder-card не используется — можно удалить из components.css")
    print("  • Если .tabs и .tab-content не используются — можно удалить из layout.css")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print("=" * 76)


if __name__ == "__main__":
    main()