#!/usr/bin/env python3
"""
136. update_scripts/136_add_hls_retry.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Добавляет retry в hls.js при ошибке 404 (m3u8 не готов).

ПРОБЛЕМА:
  PATCH-124 устанавливает status='в_сети' сразу после ffprobe,
  но ffmpeg ещё не создал index.m3u8 → 404 → hls.js "умирает".

РЕШЕНИЕ:
  При 404 ошибке делаем retry через 2 секунды (ffmpeg успеет
  создать первый сегмент).

ЗАПУСК: python update_scripts/136_add_hls_retry.py
"""

import sys
import re
from pathlib import Path


def main():
    project_root = Path.cwd()
    camera_card = project_root / "frontend/src/components/CameraCard.jsx"

    print("=" * 76)
    print("136: Retry при 404 (ffmpeg запускается)")
    print("=" * 76)
    print()

    backup = camera_card.with_suffix(".jsx.bak-136")
    backup.write_text(camera_card.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = camera_card.read_text(encoding="utf-8")

    if "PATCH-136" in content:
        print("  [OK] Патч уже применён")
        return

    # ========================================================================
    # Ищем блок обработки ошибок hls.js и добавляем retry при 404
    # ========================================================================
    # Типичная структура:
    #   hls.on(Hls.Events.ERROR, (event, data) => {
    #     if (data.fatal) {
    #       setError('Поток недоступен')
    #       hls.destroy()
    #       hlsRef.current = null
    #     }
    #   })

    old_error_handler = re.compile(
        r"(hls\.on\(Hls\.Events\.ERROR,\s*\(event,\s*data\)\s*=>\s*\{\s*)"
        r"(if\s*\(data\.fatal\)\s*\{)",
        re.DOTALL
    )

    new_error_handler = (
        r"\1"
        r"// PATCH-136: retry при 404 (ffmpeg ещё не создал m3u8)\n"
        r"      if (data.type === Hls.ErrorTypes.NETWORK_ERROR && data.response && data.response.code === 404) {\n"
        r"        console.log(`🔄 ${camera.id}: retry m3u8 через 2 сек (ffmpeg запускается)`)\n"
        r"        setTimeout(() => {\n"
        r"          if (hlsRef.current) hlsRef.current.loadSource(streamUrl)\n"
        r"        }, 2000)\n"
        r"        return\n"
        r"      }\n"
        r"      \2"
    )

    content, n = old_error_handler.subn(new_error_handler, content)

    if n:
        print(f"  [OK] Обработчик ошибок обновлён ({n} шт.)")
    else:
        # Пробуем другой вариант
        if "hls.on(Hls.Events.ERROR" in content and "data.fatal" in content:
            # Простая вставка
            content = content.replace(
                "hls.on(Hls.Events.ERROR, (event, data) => {\n        if (data.fatal) {",
                "hls.on(Hls.Events.ERROR, (event, data) => {\n"
                "        // PATCH-136: retry при 404 (ffmpeg ещё не создал m3u8)\n"
                "        if (data.type === Hls.ErrorTypes.NETWORK_ERROR && data.response && data.response.code === 404) {\n"
                "          console.log(`🔄 ${camera.id}: retry m3u8 через 2 сек`)\n"
                "          setTimeout(() => {\n"
                "            if (hlsRef.current) hlsRef.current.loadSource(streamUrl)\n"
                "          }, 2000)\n"
                "          return\n"
                "        }\n"
                "        if (data.fatal) {"
            )
            print("  [OK] Обработчик ошибок обновлён (вариант 2)")
        else:
            print("  [WARN] Обработчик ошибок не найден")
            print("  Пришлите: grep -A 10 'Hls.Events.ERROR' frontend/src/components/CameraCard.jsx")

    # ========================================================================
    # Проверка
    # ========================================================================
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
        sys.exit(1)

    if "PATCH-136" not in content:
        print("  [FAIL] маркер PATCH-136 не добавлен")
        camera_card.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)
    print("  [OK] маркер PATCH-136 на месте")

    camera_card.write_text(content, encoding="utf-8")
    print("  [OK] Файл сохранён")
    print()

    print("=" * 76)
    print("✅ Готово! Retry при 404 добавлен.")
    print()
    print("Как теперь работает:")
    print("  1. PATCH-124: status = 'в_сети' (после ffprobe)")
    print("  2. PATCH-134: hls.js инициализируется (status в зависимостях)")
    print("  3. hls.js запрашивает m3u8 → 404 (ffmpeg ещё не создал)")
    print("  4. PATCH-136: retry через 2 сек → m3u8 есть → ВИДЕО! ✅")
    print()
    print("Пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print("Обновите браузер (Ctrl+Shift+R)")
    print("=" * 76)


if __name__ == "__main__":
    main()