# ============================================================
#  GRYPHONE — общая библиотека для скриптов обновления
#  ------------------------------------------------------------
#  Подключается в начале каждого скрипта:
#    source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_lib.sh"
#
#  Предоставляет:
#    • Надёжное определение Python (без Windows Store)
#    • Функции логирования
#    • Определение корня проекта
#    • Безопасные проверки файлов (режим "не разрушать")
# ============================================================

# Корень проекта (скрипты лежат в update_scripts/)
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$LIB_DIR")}"

# ---------- Логирование ----------
log_info()  { echo "ℹ️  $*"; }
log_ok()    { echo "  ✔ $*"; }
log_warn()  { echo "⚠️  $*"; }
log_error() { echo "❌ $*" >&2; }

# ---------- Надёжное определение Python ----------
# На Windows команды `python3` часто нет, и система открывает
# Microsoft Store ("python install manager"). Поэтому проверяем
# несколько вариантов и берём первый реально работающий.
_detect_python() {
    local cmd
    for cmd in python python3 py; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" --version >/dev/null 2>&1; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    # Отдельно пробуем `py -3` (Windows Python Launcher)
    if command -v py >/dev/null 2>&1; then
        if py -3 --version >/dev/null 2>&1; then
            echo "py -3"
            return 0
        fi
    fi
    return 1
}

PYTHON="$(_detect_python || true)"

# Завершить работу, если Python не найден, с подсказкой.
require_python() {
    if [ -z "$PYTHON" ]; then
        log_error "Не найден работающий интерпретатор Python."
        echo "   Установите Python: https://www.python.org/downloads/"
        echo "   и поставьте галочку 'Add Python to PATH' при установке."
        echo ""
        echo "   Если вместо запуска открывается Microsoft Store:"
        echo "   Параметры → Приложения → Дополнительные возможности →"
        echo "   Псевдонимы выполнения приложений → отключите"
        echo "   'Установщик приложений' (python.exe / python3.exe)"
        exit 1
    fi
    log_info "Интерпретатор Python: $PYTHON ($($PYTHON --version 2>&1))"
}

# ---------- Безопасные проверки файлов ----------
# Проверить, что файл создан и не пуст (иначе выйти с ошибкой).
require_file() {
    local f="$1"
    if [ ! -s "$PROJECT_DIR/$f" ]; then
        log_error "Файл $f пуст или не создан!"
        exit 1
    fi
    log_ok "$f"
}

# Вернуть 0, если файла ещё нет (можно создавать), иначе 1.
# Использование:  if create_if_missing "app/x.py"; then ... fi
create_if_missing() {
    local target="$1"
    if [ -e "$PROJECT_DIR/$target" ]; then
        log_warn "$target уже существует — пропускаю (режим 'не разрушать')"
        return 1
    fi
    return 0
}

# Создать директорию, если её нет.
ensure_dir() {
    local d="$1"
    mkdir -p "$PROJECT_DIR/$d"
}
