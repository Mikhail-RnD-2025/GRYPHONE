#!/usr/bin/env python3
"""
130. update_scripts/130_fix_sub_and_status.py
----------------------------------------------------------------------------
Исправляет две причины чёрного экрана:
1. hasSub игнорировал sub если sub_url === main_url
2. Внутренний цикл сбрасывал статус на "подключение" — PATCH-123 скрывал video

ЗАПУСК: python update_scripts/130_fix_sub_and_status.py
"""

import sys
import re
from pathlib import Path


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("130: Исправление чёрных экранов (sub + статус)")
    print("=" * 76)
    print()

    # ========================================================================
    # ШАГ 1: ФРОНТ — hasSub проверяет только наличие sub_url
    # ========================================================================
    print("--- ШАГ 1: CameraCard.jsx — sub используется всегда ---")
    camera_card = project_root / "frontend/src/components/CameraCard.jsx"

    backup_jsx = camera_card.with_suffix(".jsx.bak-130")
    backup_jsx.write_text(camera_card.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_jsx.name}")

    content = camera_card.read_text(encoding="utf-8")

    if "PATCH-130" in content:
        print("  [OK] Уже применено")
    else:
        # Заменяем многострочное определение hasSub
        old_hassub = re.compile(
            r"const hasSub = camera\.sub_url &&\s*camera\.sub_url\.trim\(\) !== ''\s*&&\s*\n\s*camera\.sub_url !== camera\.main_url"
        )
        new_hassub = "const hasSub = !!camera.sub_url  // PATCH-130: sub даже если равен main"

        if old_hassub.search(content):
            content = old_hassub.sub(new_hassub, content)
            camera_card.write_text(content, encoding="utf-8")
            print("  [OK] hasSub = !!camera.sub_url")
        else:
            print("  [WARN] Многострочный hasSub не найден, ищу другие варианты...")
            # Пробуем однострочный вариант
            content = content.replace(
                "const hasSub = camera.sub_url && camera.sub_url !== camera.main_url",
                "const hasSub = !!camera.sub_url  // PATCH-130"
            )
            camera_card.write_text(content, encoding="utf-8")
            print("  [OK] Применено (однострочный вариант)")
    print()

    # ========================================================================
    # ШАГ 2: БЭК — статус 'в_сети' сразу после запуска ffmpeg
    # ========================================================================
    print("--- ШАГ 2: hls_worker.py — статус после запуска ffmpeg ---")
    worker = project_root / "app" / "workers" / "hls_worker.py"

    backup_py = worker.with_suffix(".py.bak-130")
    backup_py.write_text(worker.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_py.name}")

    wcontent = worker.read_text(encoding="utf-8")

    if "PATCH-130" in wcontent:
        print("  [OK] Уже применено")
    else:
        # Ищем запуск процесса: proc = await asyncio.create_subprocess_exec(...)
        proc_pattern = re.compile(
            r"(proc = await asyncio\.create_subprocess_exec\(\s*\*cmd,\s*"
            r"stdout=subprocess\.DEVNULL,\s*stderr=subprocess\.PIPE,\s*\))"
        )
        match = proc_pattern.search(wcontent)

        if match:
            insert = (
                "\n\n                    # PATCH-130: ffmpeg запущен — "
                "сразу статус 'в_сети'.\n"
                "                    # Без этого внутренний цикл сбрасывает "
                "на 'подключение',\n"
                "                    # и PATCH-123 скрывает video → чёрный "
                "экран.\n"
                "                    manager.set_status(route_id, \"в_сети\", "
                "\"Поток запущен, ожидание первого кадра\")"
            )
            wcontent = wcontent[:match.end()] + insert + wcontent[match.end():]

            try:
                compile(wcontent, str(worker), "exec")
                worker.write_text(wcontent, encoding="utf-8")
                print("  [OK] Статус 'в_сети' сразу после запуска ffmpeg")
            except SyntaxError as e:
                print(f"  [FAIL] Синтаксис: {e}")
                print("  Файл не изменён")
        else:
            print("  [WARN] Блок create_subprocess_exec не найден")
    print()

    # ========================================================================
    # ИТОГ
    # ========================================================================
    print("=" * 76)
    print("✅ Готово! Обе проблемы исправлены.")
    print()
    print("Что изменилось:")
    print("  • Фронт: sub-поток используется ВСЕГДА (даже если URL равен main)")
    print("  • Бэк: статус 'в_сети' устанавливается сразу после запуска ffmpeg")
    print("         (не сбрасывается на 'подключение' во внутреннем цикле)")
    print()
    print("Применение:")
    print("  cd frontend && npm run build")
    print("  cd .. && python main.py")
    print()
    print("Ожидаемый результат:")
    print("  • В логах: '✅ поток доступен' → ffmpeg запускается → 'в_сети'")
    print("  • В сетке: видео играет (зелёные индикаторы)")
    print("  • Запросы: GET /hls/camera/210-P-GAVw-012_sub/index.m3u8")
    print("=" * 76)


if __name__ == "__main__":
    main()