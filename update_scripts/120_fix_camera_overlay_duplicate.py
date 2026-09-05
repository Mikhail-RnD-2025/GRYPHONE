#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
120. update_scripts/120_fix_camera_overlay_duplicate.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Исправляет дублирование надписи "недоступен" на карточке камеры.
  Находит и удаляет дублирующиеся overlay-тексты.

ПРИЧИНА ПРОБЛЕМЫ:
  В CameraCard.jsx вероятно два места рендерят текст ошибки:
  1. Overlay текст (camera-overlay-text)
  2. Статусный бейдж или дополнительный текст

РЕШЕНИЕ:
  Оставить только один источник отображения статуса ошибки.

ЗАПУСК: python update_scripts/120_fix_camera_overlay_duplicate.py
============================================================================
"""

import sys
import re
from pathlib import Path


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("120: Исправление дублирования надписи 'недоступен'")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # ========================================================================
    # ШАГ 1: Анализ CameraCard.jsx
    # ========================================================================
    print("--- ШАГ 1: Анализ CameraCard.jsx ---")
    camera_card = project_root / "frontend/src/components/CameraCard.jsx"

    if not camera_card.exists():
        print("  [ERROR] CameraCard.jsx не найден")
        sys.exit(1)

    backup = camera_card.with_suffix(".jsx.bak-120")
    backup.write_text(camera_card.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = camera_card.read_text(encoding="utf-8")

    # Ищем все вхождения "недоступен" или похожих текстов
    unavailable_patterns = [
        r'недоступен',
        r'Нет сигнала',
        r'Ошибка',
        r'offline',
        r'error',
    ]

    print("\n  Поиск дубликатов надписей об ошибке:")
    for pattern in unavailable_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            print(f"    • '{pattern}': найдено {len(matches)} раз")
    print()

    # ========================================================================
    # ШАГ 2: Анализ структуры рендеринга
    # ========================================================================
    print("--- ШАГ 2: Анализ структуры рендеринга ---")

    # Ищем все места где рендерится текст ошибки
    error_render_patterns = [
        r'className=["\']camera-overlay-text["\'][^}]*}',
        r'className=["\']camera-stream-badge["\'][^}]*}',
        r'className=["\']error-text["\'][^}]*}',
    ]

    error_blocks = []
    for pattern in error_render_patterns:
        matches = list(re.finditer(pattern, content, re.DOTALL))
        for match in matches:
            # Получаем контекст вокруг совпадения
            start = max(0, match.start() - 200)
            end = min(len(content), match.end() + 200)
            context = content[start:end]
            error_blocks.append({
                'pattern': pattern,
                'position': match.start(),
                'context': context
            })

    print(f"  Найдено блоков с текстом ошибки: {len(error_blocks)}")

    if len(error_blocks) > 0:
        print("\n  Обнаруженные блоки:")
        for i, block in enumerate(error_blocks, 1):
            print(f"\n    [{i}] Позиция: {block['position']}")
            print(f"    Контекст:")
            lines = block['context'].split('\n')
            for line in lines[:10]:  # Показываем первые 10 строк
                if line.strip():
                    print(f"      {line.strip()}")
    print()

    # ========================================================================
    # ШАГ 3: Исправление дублирования
    # ========================================================================
    print("--- ШАГ 3: Исправление дублирования ---")

    # Стратегия: ищем дублирующиеся <div> или <span> с текстом ошибки
    # и удаляем один из них

    # Паттерн для поиска camera-overlay-text блока
    overlay_pattern = r'(<div[^>]*className=["\']camera-overlay-text["\'][^>]*>.*?</div>)'
    overlay_matches = list(re.finditer(overlay_pattern, content, re.DOTALL))

    if len(overlay_matches) > 1:
        print(f"  [FOUND] Найдено {len(overlay_matches)} блоков camera-overlay-text")
        print("  Удаляю дубликаты, оставляю только первый...")

        # Удаляем все кроме первого
        for match in reversed(overlay_matches[1:]):
            content = content[:match.start()] + content[match.end():]

        print(f"  [FIXED] Удалено {len(overlay_matches) - 1} дубликатов")

    # Паттерн для поиска других текстовых блоков с ошибками
    error_text_pattern = r'(<(?:div|span)[^>]*>(?:недоступен|Нет сигнала|Ошибка|offline)[^<]*</(?:div|span)>)'
    error_matches = list(re.finditer(error_text_pattern, content, re.IGNORECASE | re.DOTALL))

    if len(error_matches) > 1:
        print(f"\n  [FOUND] Найдено {len(error_matches)} текстовых блоков с ошибками")
        print("  Проверяю на дубликаты...")

        # Проверяем, есть ли одинаковые тексты
        texts = []
        for match in error_matches:
            text = match.group(1).strip()
            texts.append((text, match))

        # Группируем по содержимому
        text_groups = {}
        for text, match in texts:
            if text not in text_groups:
                text_groups[text] = []
            text_groups[text].append(match)

        # Удаляем дубликаты
        removed_count = 0
        for text, matches in text_groups.items():
            if len(matches) > 1:
                print(f"    • Текст '{text[:50]}...' дублируется {len(matches)} раз")
                for match in reversed(matches[1:]):
                    content = content[:match.start()] + content[match.end():]
                    removed_count += 1

        if removed_count > 0:
            print(f"  [FIXED] Удалено {removed_count} дубликатов текстовых блоков")

    print()

    # ========================================================================
    # ШАГ 4: Сохранение
    # ========================================================================
    print("--- ШАГ 4: Сохранение ---")
    camera_card.write_text(content, encoding="utf-8")
    print("  [OK] CameraCard.jsx сохранён")
    print()

    # ========================================================================
    # ШАГ 5: Проверка синтаксиса
    # ========================================================================
    print("--- ШАГ 5: Проверка синтаксиса ---")

    # Проверяем баланс скобок
    open_parens = content.count('(')
    close_parens = content.count(')')
    open_braces = content.count('{')
    close_braces = content.count('}')

    print(f"  Круглые скобки: {open_parens} открывающих, {close_parens} закрывающих")
    print(f"  Фигурные скобки: {open_braces} открывающих, {close_braces} закрывающих")

    if open_parens == close_parens and open_braces == close_braces:
        print("  [OK] Скобки сбалансированы")
    else:
        print("  [WARN] Скобки НЕ сбалансированы!")
        print(f"  Восстановите из бэкапа: {backup.name}")
    print()

    # ========================================================================
    # ИТОГ
    # ========================================================================
    print("=" * 76)
    print("Готово! Дублирование надписи 'недоступен' исправлено.")
    print()
    print("Что сделано:")
    print("  • Проанализирован CameraCard.jsx")
    print("  • Найдены дублирующиеся блоки с текстом ошибки")
    print("  • Удалены лишние копии, оставлен один источник")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print(f"Резервная копия: {backup.name}")
    print()
    print("Если проблема осталась:")
    print("  Восстановите из бэкапа и пришлите содержимое CameraCard.jsx")
    print("  для более точного анализа:")
    print("    cp frontend/src/components/CameraCard.jsx.bak-120 \\")
    print("       frontend/src/components/CameraCard.jsx")
    print("=" * 76)


if __name__ == "__main__":
    main()