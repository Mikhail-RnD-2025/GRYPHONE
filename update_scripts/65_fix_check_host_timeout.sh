#!/bin/sh
# ============================================================================
# 65. update_scripts/65_fix_check_host_timeout.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Патч для МОДУЛЬНОЙ версии проекта (структура из репозитория на GitHub).
#   Гарантирует, что функция проверки хоста в стримере принимает параметр
#   `timeout`, а все её вызовы передают этот параметр.
#
# ЦЕЛЕВАЯ СТРУКТУРА (новая версия):
#   app/utils/ffmpeg.py          -> определение check_host
#   app/workers/hls_worker.py    -> вызов check_host(...)
#
# ЗАЧЕМ:
#   Если определение функции не принимает `timeout`, а вызов его передаёт,
#   возникает ошибка:
#     TypeError: check_host() got an unexpected keyword argument 'timeout'
#   Из-за неё падают ВСЕ воркеры захвата потоков, сегменты не создаются,
#   а фронтенд показывает чёрный экран.
#
# ИДЕМПОТЕНТНОСТЬ:
#   Патч можно запускать многократно. Если параметр уже есть — изменения
#   не вносятся. Это безопасно для применения поверх актуального кода.
#
# БЕЗОПАСНОСТЬ:
#   Перед изменением каждого файла создаётся резервная копия `.bak-65`.
#
# ЗАВИСИМОСТИ:
#   Требуется установленный `perl` (стандартно есть в Linux/macOS,
#   в Windows — через Git Bash / MSYS2).
#
# ЗАПУСК:
#   ./65_fix_check_host_timeout.sh
#
# РЕЗУЛЬТАТ:
#   - [OK]    если всё уже корректно, ничего не меняется;
#   - [FIX]   если внесены правки (созданы .bak-65 копии).
# ============================================================================

# Прерываем работу при любой ошибке и при необъявленных переменных.
set -eu

# --- Определяем пути --------------------------------------------------------
# Папка, где лежит сам скрипт (работает независимо от места запуска).
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# Корень проекта — родитель папки update_scripts.
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# Целевые файлы в модульной структуре проекта.
FFMPEG_FILE="$PROJECT_ROOT/app/utils/ffmpeg.py"
WORKER_FILE="$PROJECT_ROOT/app/workers/hls_worker.py"

echo "============================================================================"
echo "65: Патч check_host / timeout (модульная версия)"
echo "Корень проекта : $PROJECT_ROOT"
echo "Файл утилит    : $FFMPEG_FILE"
echo "Файл воркера   : $WORKER_FILE"
echo "============================================================================"

# --- Проверяем наличие нужных инструментов ----------------------------------
# grep ищем файлы, perl выполняет аккуратную замену текста.
if ! command -v grep >/dev/null 2>&1; then
    echo "ОШИБКА: не найден grep" >&2
    exit 1
fi
if ! command -v perl >/dev/null 2>&1; then
    echo "ОШИБКА: не найден perl. Установите его (например: sudo apt install perl)" >&2
    exit 1
fi

# --- Проверяем, что целевые файлы существуют --------------------------------
# Если файлов нет — значит структура проекта отличается, патч неприменим.
if [ ! -f "$FFMPEG_FILE" ]; then
    echo "ОШИБКА: не найден файл $FFMPEG_FILE" >&2
    echo "Патч рассчитан на модульную структуру проекта (папка app/)." >&2
    exit 1
fi
if [ ! -f "$WORKER_FILE" ]; then
    echo "ОШИБКА: не найден файл $WORKER_FILE" >&2
    echo "Патч рассчитан на модульную структуру проекта (папка app/)." >&2
    exit 1
fi

# ============================================================================
# ШАГ 1. Проверяем ОПРЕДЕЛЕНИЕ функции в app/utils/ffmpeg.py
# ============================================================================
# Ищем строку определения функции (с подчёркиванием или без).
# Пример корректной сигнатуры:
#   async def check_host(url: str, timeout: float = 2.0) -> bool:
echo ""
echo "--- ШАГ 1: проверка определения функции в $FFMPEG_FILE ---"

# Находим строки с определением функции проверки хоста.
DEF_LINES=$(grep -n "def _*check_host" "$FFMPEG_FILE" || true)

if [ -z "$DEF_LINES" ]; then
    echo "[FAIL] В файле не найдено определение функции check_host." >&2
    echo "       Проверьте структуру проекта." >&2
    exit 1
fi

echo "Найдено определение:"
echo "$DEF_LINES"

# Проверяем, есть ли параметр `timeout` в сигнатуре.
# Если в строке определения есть слово `timeout` — всё уже корректно.
if echo "$DEF_LINES" | grep -q "timeout"; then
    echo "[OK] Определение уже содержит параметр timeout. Файл не трогаем."
    DEF_FIXED=1
else
    echo "[FIX] В определении нет параметра timeout — добавляем."

    # Резервная копия ПЕРЕД изменением.
    cp "$FFMPEG_FILE" "$FFMPEG_FILE.bak-65"
    echo "[BAK] Создана резервная копия: $FFMPEG_FILE.bak-65"

    # --- Применяем патчи через perl -----------------------------------------
    # Покрываем несколько вариантов написания сигнатуры, чтобы патч был
    # устойчив к форматированию кода.

    # Вариант 1: с аннотацией типа
    #   async def check_host(url: str) -> bool:
    #   ->
    #   async def check_host(url: str, timeout: float = 2.0) -> bool:
    perl -pi -e 's/async def check_host\(\s*url\s*:\s*str\s*\)/async def check_host(url: str, timeout: float = 2.0)/g' "$FFMPEG_FILE"

    # Вариант 2: без аннотации, без подчёркивания
    #   async def check_host(url):  ->  async def check_host(url, timeout=2.0):
    perl -pi -e 's/async def check_host\(\s*url\s*\)/async def check_host(url, timeout=2.0)/g' "$FFMPEG_FILE"

    # Вариант 3: имя с подчёркиванием, без аннотации
    #   async def _check_host(url):  ->  async def _check_host(url, timeout=2.0):
    perl -pi -e 's/async def _check_host\(\s*url\s*\)/async def _check_host(url, timeout=2.0)/g' "$FFMPEG_FILE"

    # Вариант 4: имя с подчёркиванием, с аннотацией
    #   async def _check_host(url: str) -> bool:
    #   ->
    #   async def _check_host(url: str, timeout: float = 2.0) -> bool:
    perl -pi -e 's/async def _check_host\(\s*url\s*:\s*str\s*\)/async def _check_host(url: str, timeout: float = 2.0)/g' "$FFMPEG_FILE"

    # Повторно проверяем результат применения патча.
    NEW_DEF=$(grep -n "def _*check_host" "$FFMPEG_FILE" || true)
    if echo "$NEW_DEF" | grep -q "timeout"; then
        echo "[FIXED] Параметр timeout успешно добавлен в определение."
        DEF_FIXED=1
    else
        echo "[FAIL] Не удалось добавить параметр автоматически." >&2
        echo "       Исправьте вручную в $FFMPEG_FILE:" >&2
        echo "       async def check_host(url: str, timeout: float = 2.0) -> bool:" >&2
        DEF_FIXED=0
    fi
fi

# ============================================================================
# ШАГ 2. Проверяем ВЫЗОВ функции в app/workers/hls_worker.py
# ============================================================================
# Ищем вызовы функции. В новой версии вызов выглядит так:
#   if not await check_host(url, timeout=probe_timeout):
echo ""
echo "--- ШАГ 2: проверка вызова функции в $WORKER_FILE ---"

# Находим строки с вызовом функции проверки хоста (кроме определений).
CALL_LINES=$(grep -n "check_host(" "$WORKER_FILE" | grep -v "def " || true)

if [ -z "$CALL_LINES" ]; then
    echo "[WARN] В файле воркера не найдено вызовов check_host."
    echo "       Возможно, структура изменилась. Проверьте вручную."
    CALL_OK=1
else
    echo "Найдены вызовы:"
    echo "$CALL_LINES"

    # Проверяем, передаётся ли в вызове параметр `timeout`.
    if echo "$CALL_LINES" | grep -q "timeout"; then
        echo "[OK] Вызов уже передаёт параметр timeout. Файл не трогаем."
        CALL_OK=1
    else
        echo "[FIX] Вызов не передаёт timeout — добавляем."

        # Резервная копия ПЕРЕД изменением.
        cp "$WORKER_FILE" "$WORKER_FILE.bak-65"
        echo "[BAK] Создана резервная копия: $WORKER_FILE.bak-65"

        # Добавляем параметр в вызов.
        #   await check_host(url)  ->  await check_host(url, timeout=2.0)
        perl -pi -e 's/check_host\(\s*url\s*\)/check_host(url, timeout=2.0)/g' "$WORKER_FILE"

        # Повторная проверка.
        NEW_CALLS=$(grep -n "check_host(" "$WORKER_FILE" | grep -v "def " || true)
        if echo "$NEW_CALLS" | grep -q "timeout"; then
            echo "[FIXED] Параметр timeout добавлен в вызов."
            CALL_OK=1
        else
            echo "[FAIL] Не удалось добавить параметр в вызов автоматически." >&2
            echo "       Исправьте вручную в $WORKER_FILE:" >&2
            echo "       if not await check_host(url, timeout=probe_timeout):" >&2
            CALL_OK=0
        fi
    fi
fi

# ============================================================================
# ИТОГОВЫЙ ОТЧЁТ
# ============================================================================
echo ""
echo "============================================================================"
echo "Итог:"
echo "  Определение функции : $([ "$DEF_FIXED" -eq 1 ] && echo 'корректно' || echo 'ТРЕБУЕТ ВНИМАНИЯ')"
echo "  Вызов в воркере     : $([ "$CALL_OK" -eq 1 ] && echo 'корректно' || echo 'ТРЕБУЕТ ВНИМАНИЯ')"
echo ""
if [ "$DEF_FIXED" -eq 1 ] && [ "$CALL_OK" -eq 1 ]; then
    echo "ПАТЧ ПРИМЕНЁН УСПЕШНО (или изменения не потребовались)."
    echo "Резервные копии имеют суффикс .bak-65"
    exit 0
else
    echo "ПАТЧ ЗАВЕРШЁН С ПРЕДУПРЕЖДЕНИЯМИ. Проверьте сообщения [FAIL] выше."
    exit 1
fi