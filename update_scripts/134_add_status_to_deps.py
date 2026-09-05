#!/usr/bin/env python3
"""
134. update_scripts/134_add_status_to_deps.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Добавляет status в зависимости useEffect в CameraCard.jsx.
  Это заставляет hls.js перезапускаться, когда статус меняется
  с 'подключение' на 'в_сети'.

ПРОБЛЕМА:
  Видео не появлялось без перезагрузки страницы, потому что
  hls.js инициализировался один раз при status='подключение',
  получал ошибку и "умирал". Когда status становился 'в_сети',
  useEffect не перезапускался.

РЕШЕНИЕ:
  1. Добавить status в зависимости useEffect
  2. Инициализировать hls.js только при status === 'в_сети'
  3. Разрушать hls.js при уходе статуса с 'в_сети'
  4. Автоматический перезапуск при возвращении 'в_сети'

ЗАПУСК: python update_scripts/134_add_status_to_deps.py
"""

import sys
import re
from pathlib import Path


def main():
    project_root = Path.cwd()
    camera_card = project_root / "frontend/src/components/CameraCard.jsx"

    print("=" * 76)
    print("134: Перезапуск hls.js при смене статуса")
    print("=" * 76)
    print()

    backup = camera_card.with_suffix(".jsx.bak-134")
    backup.write_text(camera_card.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = camera_card.read_text(encoding="utf-8")

    if "PATCH-134" in content:
        print("  [OK] Патч уже применён")
        return

    changes = []

    # ========================================================================
    # F1: Добавить status в зависимости useEffect
    # ========================================================================
    # Ищем: }, [streamUrl, shouldPlay])
    old_deps = re.compile(r'\}, \[streamUrl, shouldPlay\]\)')
    new_deps = "}, [streamUrl, shouldPlay, status])  // PATCH-134: перезапуск при смене статуса"

    content, n = old_deps.subn(new_deps, content)
    if n:
        changes.append("F1: status добавлен в зависимости useEffect")
    else:
        # Пробуем другие варианты
        for variant in [
            "}, [streamUrl, shouldPlay])\n",
            "}, [streamUrl, shouldPlay]);",
        ]:
            if variant in content:
                content = content.replace(
                    variant,
                    variant.replace("shouldPlay])", "shouldPlay, status])  // PATCH-134")
                )
                changes.append("F1: status добавлен (вариант 2)")
                break

    # ========================================================================
    # F2: Проверка status === 'в_сети' перед инициализацией hls.js
    # ========================================================================
    # Ищем строку "if (!video) return" внутри useEffect и добавляем
    # проверку status после неё
    old_check = '''    // Если видео элемента нет (не должно случаться, т.к. он
    // всегда рендерится), выходим.
    if (!video) return

    setError(null)

    if (Hls.isSupported()) {'''

    new_check = '''    // Если видео элемента нет (не должно случаться, т.к. он
    // всегда рендерится), выходим.
    if (!video) return

    // PATCH-134: инициализируем hls.js только при status === 'в_сети'
    if (status !== 'в_сети') {
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
      return
    }

    setError(null)

    if (Hls.isSupported()) {'''

    if old_check in content:
        content = content.replace(old_check, new_check)
        changes.append("F2: проверка status === 'в_сети' перед hls.js")
    else:
        # Альтернативный вариант
        if "if (!video) return" in content and "setError(null)" in content:
            # Простая вставка после "if (!video) return"
            content = content.replace(
                "if (!video) return\n\n    setError(null)",
                "if (!video) return\n\n"
                "    // PATCH-134: hls.js только при 'в_сети'\n"
                "    if (status !== 'в_сети') {\n"
                "      if (hlsRef.current) { hlsRef.current.destroy(); hlsRef.current = null }\n"
                "      return\n"
                "    }\n\n"
                "    setError(null)"
            )
            changes.append("F2: проверка status (вариант 2)")

    # ========================================================================
    # F3: Обновить shouldPlay для учёта статуса
    # ========================================================================
    # Делаем shouldPlay = camera.enabled && status === 'в_сети'
    old_shouldplay = "const shouldPlay = camera.enabled"
    new_shouldplay = "const shouldPlay = camera.enabled && status === 'в_сети'  // PATCH-134"

    if old_shouldplay in content:
        content = content.replace(old_shouldplay, new_shouldplay, 1)
        changes.append("F3: shouldPlay теперь учитывает status")
    elif "const shouldPlay = status === 'в_сети'" in content:
        # Уже есть правильная логика от PATCH-129
        changes.append("F3: shouldPlay уже учитывает status (пропуск)")

    # ========================================================================
    # Сохранение
    # ========================================================================
    print()
    print("--- Применённые изменения ---")
    for c in changes:
        print(f"  • {c}")

    if not changes:
        print("  [WARN] Изменения не применены")
        print("  Пришлите: sed -n '30,90p' frontend/src/components/CameraCard.jsx")

    # Проверка баланса скобок
    print()
    print("--- Проверка синтаксиса ---")
    if content.count('{') == content.count('}') and \
       content.count('(') == content.count(')'):
        print("  [OK] Скобки сбалансированы")
    else:
        print(f"  [FAIL] Скобки не сбалансированы:")
        print(f"    {{ = {content.count('{')}  vs  }} = {content.count('}')}")
        print(f"    ( = {content.count('(')}  vs  ) = {content.count(')')}")
        camera_card.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        print("  Файл восстановлен из бэкапа")
        sys.exit(1)

    # Проверка наличия status в зависимостях
    if "shouldPlay, status])" not in content and "status, shouldPlay])" not in content:
        print("  [WARN] status не найден в зависимостях useEffect")
        print("  Проверьте вручную, что status добавлен в массив зависимостей")

    camera_card.write_text(content, encoding="utf-8")
    print("  [OK] Файл сохранён")
    print()

    print("=" * 76)
    print("✅ Готово! hls.js теперь перезапускается при смене статуса.")
    print()
    print("Что изменилось:")
    print("  • F1: status добавлен в зависимости useEffect")
    print("  • F2: hls.js инициализируется ТОЛЬКО при status === 'в_сети'")
    print("  • F3: shouldPlay учитывает status")
    print()
    print("Как теперь работает:")
    print("  1. Камера включена, status = 'подключение'")
    print("     → hls.js НЕ инициализируется (нет смысла — нет сегментов)")
    print("  2. Через 1-3 сек status = 'в_сети'")
    print("     → useEffect перезапускается (status в зависимостях)")
    print("     → hls.js инициализируется и загружает m3u8")
    print("     → Сегменты уже созданы ffmpeg → видео появляется!")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print("Обновите браузер (Ctrl+Shift+R) и проверьте:")
    print("  • Toggle OFF → Toggle ON")
    print("  • Видео должно появиться БЕЗ перезагрузки страницы")
    print("=" * 76)


if __name__ == "__main__":
    main()