#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
122. update_scripts/122_add_stream_timeout.py
----------------------------------------------------------------------------
НАЗНАЧЕНИЕ:
  Добавляет таймаут подключения RTSP-потока (10 секунд) в стример.

ПРОБЛЕМА:
  cv2.VideoCapture(url) может блокироваться бесконечно, из-за чего
  камера навсегда застревает в статусе 'подключение'.

РЕШЕНИЕ:
  1. Подключение выполняется в отдельном потоке с join(timeout=10)
  2. При таймауте возвращается заглушка _TimeoutCap (isOpened() = False)
  3. Существующая логика стримера сама переведёт камеру в 'недоступна'

ИДЕМПОТЕНТНОСТЬ: маркер PATCH-122, повторный запуск безопасен.
ЗАПУСК: python update_scripts/122_add_stream_timeout.py
============================================================================
"""

import sys
import re
from pathlib import Path


def main():
    project_root = Path.cwd()

    print("=" * 76)
    print("122: Таймаут подключения RTSP-потока (10 сек)")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # ========================================================================
    # ШАГ 1: Поиск файлов стримера
    # ========================================================================
    print("--- ШАГ 1: Поиск файлов с cv2.VideoCapture ---")

    target_files = []
    for py_file in project_root.rglob("*.py"):
        # Пропускаем бэкапы, node_modules, update_scripts
        if any(part in str(py_file) for part in ['.bak', 'node_modules', 'update_scripts', '.git', 'venv', 'dist']):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue
        if "cv2.VideoCapture" in content:
            target_files.append(py_file)

    if not target_files:
        print("  [ERROR] Файлы с cv2.VideoCapture не найдены")
        sys.exit(1)

    for f in target_files:
        print(f"  [FOUND] {f.relative_to(project_root)}")
    print()

    # ========================================================================
    # ШАГ 2: Применение таймаута
    # ========================================================================
    print("--- ШАГ 2: Применение таймаута ---")

    timeout_helper = '''
# ============================================================
# PATCH-122: Таймаут подключения RTSP-потока
# ============================================================
STREAM_CONNECT_TIMEOUT = 10  # секунд на попытку подключения


class _TimeoutCap:
    """Заглушка для случая, когда поток не открылся за таймаут."""
    def isOpened(self):
        return False
    def isOpened_(self):
        return False
    def release(self):
        pass
    def read(self):
        return False, None
    def set(self, *args, **kwargs):
        return False
    def get(self, *args, **kwargs):
        return 0


def open_stream_with_timeout(url, timeout=STREAM_CONNECT_TIMEOUT):
    """
    Открывает видеопоток с таймаутом.
    Возвращает объект VideoCapture или _TimeoutCap при неудаче/таймауте.
    """
    import threading
    result = {}

    def _opener():
        try:
            cap = cv2.VideoCapture(url)
            result["cap"] = cap
            result["ok"] = cap.isOpened()
        except Exception:
            result["cap"] = None
            result["ok"] = False

    thread = threading.Thread(target=_opener, daemon=True)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        # Подключение заняло больше таймаута — считаем камеру недоступной
        return _TimeoutCap()

    if result.get("ok") and result.get("cap") is not None:
        return result["cap"]
    return _TimeoutCap()
# ============================================================
# Конец PATCH-122
# ============================================================
'''

    for py_file in target_files:
        print(f"\n  Обработка: {py_file.relative_to(project_root)}")

        # Бэкап
        backup = py_file.with_suffix(py_file.suffix + ".bak-122")
        backup.write_text(py_file.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"    [BAK] {backup.name}")

        content = py_file.read_text(encoding="utf-8")

        # Идемпотентность
        if "PATCH-122" in content:
            print("    [OK] Таймаут уже применён (маркер PATCH-122)")
            continue

        changes = []

        # 1. Добавляем import threading, если нет
        if "import threading" not in content:
            # Вставляем после первого import cv2 или первого import
            if "import cv2" in content:
                content = content.replace("import cv2", "import cv2\nimport threading", 1)
            else:
                content = re.sub(r'(import [a-zA-Z_]+)', r'import threading\n\1', content, count=1)
            changes.append("добавлен import threading")

        # 2. Вставляем функцию таймаута после импортов
        # Находим позицию после последнего import в начале файла
        import_matches = list(re.finditer(r'^(?:import|from)\s.+$', content, re.MULTILINE))
        if import_matches:
            insert_pos = import_matches[-1].end()
            content = content[:insert_pos] + "\n" + timeout_helper + content[insert_pos:]
            changes.append("вставлена функция open_stream_with_timeout")
        else:
            content = timeout_helper + "\n" + content
            changes.append("вставлена функция open_stream_with_timeout (в начало)")

        # 3. Заменяем cv2.VideoCapture( на open_stream_with_timeout(
        count_before = content.count("cv2.VideoCapture(")
        content = content.replace("cv2.VideoCapture(", "open_stream_with_timeout(")
        # Но НЕ заменяем внутри самой функции-хелпера (там должен остаться cv2.VideoCapture)
        # Возвращаем оригинал внутри хелпера
        content = content.replace(
            "cap = open_stream_with_timeout(url)",
            "cap = cv2.VideoCapture(url)"
        )
        count_after = count_before - 1 if count_before > 0 else 0
        changes.append(f"заменено вызовов VideoCapture: {count_after}")

        py_file.write_text(content, encoding="utf-8")

        for change in changes:
            print(f"    [FIXED] {change}")

    print()

    # ========================================================================
    # ШАГ 3: Проверка синтаксиса
    # ========================================================================
    print("--- ШАГ 3: Проверка синтаксиса ---")
    all_ok = True
    for py_file in target_files:
        try:
            compile(py_file.read_text(encoding="utf-8"), str(py_file), "exec")
            print(f"  [OK] {py_file.relative_to(project_root)}: синтаксис корректен")
        except SyntaxError as e:
            print(f"  [FAIL] {py_file.relative_to(project_root)}: {e}")
            backup = py_file.with_suffix(py_file.suffix + ".bak-122")
            print(f"         Восстановите: cp {backup} {py_file}")
            all_ok = False
    print()

    # ========================================================================
    # ИТОГ
    # ========================================================================
    print("=" * 76)
    if not all_ok:
        print("ВНИМАНИЕ: обнаружены ошибки синтаксиса — восстановите из бэкапов!")
        print("=" * 76)
        sys.exit(1)

    print("Готово! Таймаут подключения добавлен.")
    print()
    print("Как это работает:")
    print("  1. Воркер вызывает open_stream_with_timeout(url)")
    print("  2. Подключение идёт в отдельном потоке, ожидание максимум 10 сек")
    print("  3. Если поток не открылся за 10 сек — возвращается заглушка")
    print("  4. isOpened() = False → стример переводит камеру в 'недоступна'")
    print()
    print("Результат:")
    print("  • Камеры больше НЕ застревают в 'подключение' навсегда")
    print("  • Через ~10 сек недоступная камера получает статус 'недоступна'")
    print()
    print("Перезапустите сервер:")
    print("  python main.py")
    print("=" * 76)


if __name__ == "__main__":
    main()