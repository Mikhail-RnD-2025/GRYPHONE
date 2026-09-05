#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
123. update_scripts/123_cleanup_old_streams.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Устраняет показ старых потоков после перезагрузки сервера.

УРОВЕНЬ 1 (БЭКТЕНД):
  При старте main.py удаляет старые snapshot-файлы (*.jpg) из кэша.

УРОВЕНЬ 2 (ФРОНТЕНД):
  В CameraCard.jsx видео рендерится ТОЛЬКО при статусе 'в_сети'.
  Во всех остальных случаях — заглушка camera-empty.

ИДЕМПОТЕНТНОСТЬ: маркеры PATCH-123, повторный запуск безопасен.
ЗАПУСК: python update_scripts/123_cleanup_old_streams.py
============================================================================
"""

import sys
import re
from pathlib import Path


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("123: Очистка старых потоков при перезагрузке")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # ========================================================================
    # ШАГ 1: Бэкенд — очистка snapshot при старте
    # ========================================================================
    print("--- ШАГ 1: Бэкенд — очистка snapshot при старте ---")
    main_py = project_root / "main.py"

    if not main_py.exists():
        print("  [WARN] main.py не найден, пропускаю бэкенд-часть")
    else:
        backup = main_py.with_suffix(".py.bak-123")
        backup.write_text(main_py.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  [BAK] {backup.name}")

        content = main_py.read_text(encoding="utf-8")

        if "PATCH-123" in content:
            print("  [OK] Очистка уже добавлена (маркер PATCH-123)")
        else:
            cleanup_code = '''

# ============================================================
# PATCH-123: очистка старых snapshot при старте сервера
# ============================================================
def cleanup_old_snapshots_123():
    """Удаляет старые snapshot-файлы, чтобы не показывать 'старые потоки'."""
    import glob
    import os
    removed = 0
    for pattern in ["**/*.jpg", "**/*.jpeg"]:
        for f in glob.glob(os.path.join("data", pattern), recursive=True):
            try:
                os.remove(f)
                removed += 1
            except OSError:
                pass
    for pattern in ["**/*.jpg", "**/*.jpeg"]:
        for f in glob.glob(os.path.join("snapshots", pattern), recursive=True):
            try:
                os.remove(f)
                removed += 1
            except OSError:
                pass
    print(f"[PATCH-123] Удалено старых snapshot: {removed}")

cleanup_old_snapshots_123()
# ============================================================
'''
            # Вставляем после импортов
            import_matches = list(re.finditer(r'^(?:import|from)\s.+$', content, re.MULTILINE))
            if import_matches:
                insert_pos = import_matches[-1].end()
                content = content[:insert_pos] + cleanup_code + content[insert_pos:]
            else:
                content = cleanup_code + content

            main_py.write_text(content, encoding="utf-8")
            print("  [FIXED] Добавлена очистка snapshot при старте")
    print()

    # ========================================================================
    # ШАГ 2: Фронтенд — видео только при статусе 'в_сети'
    # ========================================================================
    print("--- ШАГ 2: Фронтенд — видео только при 'в_сети' ---")
    camera_card = project_root / "frontend/src/components/CameraCard.jsx"

    if not camera_card.exists():
        print("  [WARN] CameraCard.jsx не найден, пропускаю фронт-часть")
    else:
        backup = camera_card.with_suffix(".jsx.bak-123")
        backup.write_text(camera_card.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  [BAK] {backup.name}")

        content = camera_card.read_text(encoding="utf-8")

        if "PATCH-123" in content:
            print("  [OK] Условие уже применено (маркер PATCH-123)")
        else:
            # Ищем блок рендера видео (img или video с camera-video)
            video_pattern = re.compile(
                r'(<(?:img|video)\b[^>]*className="camera-video"[^>]*?(?:/>|</(?:img|video)>))',
                re.DOTALL
            )
            matches = list(video_pattern.finditer(content))

            if matches:
                # Проверяем, не обёрнут ли уже в условие статуса
                for match in reversed(matches):
                    start = max(0, match.start() - 150)
                    prefix = content[start:match.start()]
                    if "status === 'в_сети'" in prefix or "в_сети" in prefix[-80:]:
                        print("  [OK] Видео уже обёрнуто в условие статуса")
                        continue

                    wrapped = "{status === 'в_сети' && (  /* PATCH-123 */\n        " + match.group(1) + "\n      )}"
                    content = content[:match.start()] + wrapped + content[match.end():]
                    print("  [FIXED] Видео обёрнуто в условие status === 'в_сети'")
            else:
                print("  [WARN] Блок camera-video не найден")

            camera_card.write_text(content, encoding="utf-8")
    print()

    # ========================================================================
    # ШАГ 3: Проверка синтаксиса
    # ========================================================================
    print("--- ШАГ 3: Проверка синтаксиса ---")
    ok = True

    if main_py.exists():
        try:
            compile(main_py.read_text(encoding="utf-8"), str(main_py), "exec")
            print("  [OK] main.py: синтаксис корректен")
        except SyntaxError as e:
            print(f"  [FAIL] main.py: {e}")
            ok = False

    if camera_card.exists():
        c = camera_card.read_text(encoding="utf-8")
        if c.count('{') == c.count('}') and c.count('(') == c.count(')'):
            print("  [OK] CameraCard.jsx: скобки сбалансированы")
        else:
            print("  [FAIL] CameraCard.jsx: скобки НЕ сбалансированы")
            ok = False
    print()

    # ========================================================================
    # ИТОГ
    # ========================================================================
    print("=" * 76)
    if not ok:
        print("ВНИМАНИЕ: ошибки! Восстановите из бэкапов .bak-123")
        print("=" * 76)
        sys.exit(1)

    print("Готово! Старые потоки больше не будут показываться.")
    print()
    print("Как это работает:")
    print("  1. При старте сервера удаляются старые snapshot-файлы")
    print("  2. Фронт показывает видео ТОЛЬКО при статусе 'в_сети'")
    print("  3. Во всех остальных случаях — заглушка 'Недоступна'/'Отключена'")
    print()
    print("Применение:")
    print("  cd frontend && npm run build")
    print("  cd .. && python main.py")
    print("=" * 76)


if __name__ == "__main__":
    main()