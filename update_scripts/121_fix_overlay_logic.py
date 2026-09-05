#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
121. update_scripts/121_fix_overlay_logic.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  1. Восстанавливает CameraCard.jsx из бэкапа .bak-120
     (патч 120 ошибочно удалил блоки "Отключена" и "Недоступна")
  2. Исправляет НАСТОЯЩУЮ причину наложения:
     блок error теперь НЕ рендерится, когда статус 'недоступна'

ПРИЧИНА ПРОБЛЕМЫ:
  Когда камера недоступна, одновременно рендерились:
  • {error && ...} → красный текст ошибки
  • {status === 'недоступна' && ...} → текст "Недоступна"
  Оба absolute по центру → наложение.

РЕШЕНИЕ:
  Добавить условие в блок error:
  {error && !(camera.enabled && status === 'недоступна') && ...}

ЗАПУСК: python update_scripts/121_fix_overlay_logic.py
============================================================================
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("121: Исправление логики overlay-текстов")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    camera_card = project_root / "frontend/src/components/CameraCard.jsx"
    backup_120 = project_root / "frontend/src/components/CameraCard.jsx.bak-120"

    if not camera_card.exists():
        print("  [ERROR] CameraCard.jsx не найден")
        sys.exit(1)

    # ========================================================================
    # ШАГ 1: Восстановление из бэкапа .bak-120
    # ========================================================================
    print("--- ШАГ 1: Восстановление из бэкапа .bak-120 ---")

    if backup_120.exists():
        camera_card.write_text(backup_120.read_text(encoding="utf-8"), encoding="utf-8")
        print("  [OK] CameraCard.jsx восстановлен из .bak-120")
        print("  (возвращены блоки 'Отключена' и 'Недоступна')")
    else:
        print("  [WARN] Бэкап .bak-120 не найден, работаю с текущим файлом")
    print()

    # ========================================================================
    # ШАГ 2: Исправление условия блока error
    # ========================================================================
    print("--- ШАГ 2: Исправление условия блока error ---")

    content = camera_card.read_text(encoding="utf-8")

    # Ищем блок error и добавляем условие исключения
    old_error_block = """{error && (
        <div className="camera-overlay-text" style={{ color: '#dc2626' }}>
          {error}
        </div>
      )}"""

    new_error_block = """{error && !(camera.enabled && status === 'недоступна') && (
        <div className="camera-overlay-text" style={{ color: '#dc2626' }}>
          {error}
        </div>
      )}"""

    if old_error_block in content:
        content = content.replace(old_error_block, new_error_block)
        print("  [FIXED] Добавлено условие: error не показывается при статусе 'недоступна'")
    else:
        # Пробуем вариант с другим отступом
        old_error_block2 = "{error && ("
        new_error_block2 = "{error && !(camera.enabled && status === 'недоступна') && ("

        if old_error_block2 in content and new_error_block2 not in content:
            content = content.replace(old_error_block2, new_error_block2, 1)
            print("  [FIXED] Добавлено условие (вариант 2)")
        elif new_error_block2 in content:
            print("  [OK] Условие уже применено")
        else:
            print("  [WARN] Не удалось найти блок error для исправления")
    print()

    # ========================================================================
    # ШАГ 3: Сохранение и проверка
    # ========================================================================
    print("--- ШАГ 3: Сохранение и проверка ---")
    camera_card.write_text(content, encoding="utf-8")
    print("  [OK] CameraCard.jsx сохранён")

    # Проверка баланса скобок
    open_parens = content.count('(')
    close_parens = content.count(')')
    open_braces = content.count('{')
    close_braces = content.count('}')

    print(f"  Круглые скобки: {open_parens}/{close_parens}")
    print(f"  Фигурные скобки: {open_braces}/{close_braces}")

    if open_parens == close_parens and open_braces == close_braces:
        print("  [OK] Скобки сбалансированы")
    else:
        print("  [FAIL] Скобки НЕ сбалансированы!")
        print(f"  Восстановите: cp {backup_120} {camera_card}")
        sys.exit(1)
    print()

    # ========================================================================
    # ШАГ 4: Проверка логики состояний
    # ========================================================================
    print("--- ШАГ 4: Проверка логики состояний ---")

    checks = [
        ("Блок 'Отключена'", "!camera.enabled && ("),
        ("Блок 'Недоступна'", "status === 'недоступна' && ("),
        ("Блок error с условием", "!(camera.enabled && status === 'недоступна')"),
    ]

    all_ok = True
    for name, pattern in checks:
        if pattern in content:
            print(f"  [OK] {name} присутствует")
        else:
            print(f"  [WARN] {name} НЕ найден")
            all_ok = False
    print()

    # ========================================================================
    # ИТОГ
    # ========================================================================
    print("=" * 76)
    print("Готово! Логика overlay-текстов исправлена.")
    print()
    print("Теперь состояния взаимоисключающие:")
    print("  • Камера отключена        → 'Отключена'")
    print("  • Камера недоступна       → 'Недоступна' (БЕЗ красного error)")
    print("  • Другая ошибка           → красный текст error")
    print()
    print("Наложение надписей устранено!")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print("=" * 76)


if __name__ == "__main__":
    main()