#!/bin/sh
# 63. update_scripts/63_fix_sets_empty_field.sh
# 64. Исправление: если наборы не созданы, поле/блок с ними не должен исчезать.
# 65. Запуск: ./63_fix_sets_empty_field.sh [путь_к_frontend/src]

set -eu

# 66. Определяем папку скрипта
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# 67. Ищем фронтенд рядом с папкой update_scripts
if [ -d "$SCRIPT_DIR/../frontend/src" ]; then
  DEFAULT_ROOT="$SCRIPT_DIR/../frontend/src"
else
  DEFAULT_ROOT="$PWD/frontend/src"
fi

# 68. Путь к фронтенду можно передать аргументом
ROOT="${1:-$DEFAULT_ROOT}"

# 69. Проверяем наличие perl
if ! command -v perl >/dev/null 2>&1; then
  echo "Нужен perl. Например: sudo apt install perl" >&2
  exit 1
fi

# 70. Проверяем каталог фронтенда
if [ ! -e "$ROOT" ]; then
  echo "Не найден каталог фронтенда: $ROOT" >&2
  echo "Использование: $0 [путь_к_frontend/src]" >&2
  exit 1
fi

echo "Исправляю отображение наборов в: $ROOT"

# 71. Ищем исходники фронтенда, исключая служебные папки
find "$ROOT" \
  -type d \( -name node_modules -o -name dist -o -name build \) -prune \
  -o -type f \( -name '*.jsx' -o -name '*.js' -o -name '*.tsx' -o -name '*.ts' \) -print |
while read -r FILE; do
  # 72. Работаем только с файлами, где есть логика наборов
  if grep -qE 'sets(\?)?\.length|sets\.map' "$FILE"; then
    cp "$FILE" "$FILE.bak-sets"

    # 73. Защита от null/undefined при вызове sets.map
    perl -pi -e 's/\bsets\.map\(/\(sets ?? []).map(/g' "$FILE"

    # 74. Убираем условия, из-за которых весь блок исчезает при пустом списке
    perl -pi -e 's/\{\s*sets\s*&&\s*sets\?\.length\s*>\s*0\s*&&/\{sets \&\&/g' "$FILE"
    perl -pi -e 's/\{\s*sets\s*&&\s*sets\.length\s*>\s*0\s*&&/\{sets \&\&/g' "$FILE"

    # 75. Если блок начинался только с проверки длины, оставляем его видимым
    perl -pi -e 's/\{\s*sets\.length\s*>\s*0\s*&&/\{/g' "$FILE"
    perl -pi -e 's/\{\s*sets\?\.length\s*>\s*0\s*&&/\{/g' "$FILE"

    # 76. Если перед map остался лишний guard вида {sets && ..., убираем его
    perl -pi -e 's/\{\s*sets\s*&&\s*\(sets \?\? \[\]\)\.map\(/\{(sets ?? []).map(/g' "$FILE"

    # 77. Добавляем видимое пустое состояние, если его ещё нет
    if ! grep -qF 'Наборы не созданы' "$FILE"; then
      case "$FILE" in
        *.jsx|*.tsx)
          perl -pi -e 's/\{\s*\(sets \?\? \[\]\)\.map\(/\{(!sets || sets.length === 0) \&\& <div className="empty-state">Наборы не созданы<\/div>\}\n\{(sets ?? []).map(/g' "$FILE"
          ;;
      esac
    fi

    echo "Исправлен: $FILE"
  fi
done

# 78. Добавляем минимальный стиль для пустого состояния
CSS_FILE=$(find "$ROOT" -type f -name '*.css' -print | head -n 1)

if [ -n "$CSS_FILE" ]; then
  if ! grep -qF '.empty-state' "$CSS_FILE"; then
    {
      printf '%s\n' ''
      printf '%s\n' '.empty-state {'
      printf '%s\n' '  padding: 12px;'
      printf '%s\n' '  border: 1px dashed #999;'
      printf '%s\n' '  color: #666;'
      printf '%s\n' '  border-radius: 8px;'
      printf '%s\n' '}'
    } >> "$CSS_FILE"

    echo "CSS обновлён: $CSS_FILE"
  fi
fi

echo ""
echo "Готово."
echo "Проверь изменения: git diff"
echo "Резервные копии файлов имеют расширение .bak-sets"