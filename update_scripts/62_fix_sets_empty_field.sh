#!/bin/sh
# 62. /update_scripts/62_fix_sets_empty_field.sh
# 63. Исправление: если наборы не созданы, поле/блок с ними не должен исчезать.
# 64. Запуск: /update_scripts/62_fix_sets_empty_field.sh [путь_к_frontend/src]

set -eu

# 65. Определяем расположение скрипта и вероятный корень проекта
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# 66. Если скрипт лежит в <repo>/update_scripts, фронтенд ищем рядом
if [ -d "$SCRIPT_DIR/../frontend/src" ]; then
  DEFAULT_ROOT="$SCRIPT_DIR/../frontend/src"
else
  DEFAULT_ROOT="$PWD/frontend/src"
fi

# 67. Путь к фронтенду можно передать аргументом
ROOT="${1:-$DEFAULT_ROOT}"

# 68. Проверяем наличие perl
if ! command -v perl >/dev/null 2>&1; then
  echo "Нужен perl. Например: sudo apt install perl" >&2
  exit 1
fi

# 69. Проверяем каталог фронтенда
if [ ! -e "$ROOT" ]; then
  echo "Не найден каталог фронтенда: $ROOT" >&2
  echo "Использование: $0 [путь_к_frontend/src]" >&2
  exit 1
fi

echo "Исправляю отображение наборов в: $ROOT"

# 70. Ищем исходники фронтенда, исключая служебные папки
find "$ROOT" \
  -type d \( -name node_modules -o -name dist -o -name build \) -prune \
  -o -type f \( -name '*.jsx' -o -name '*.js' -o -name '*.tsx' -o -name '*.ts' \) -print |
while read -r FILE; do
  # 71. Работаем только с файлами, где есть логика наборов
  if grep -qE 'sets(\?)?\.length|sets\.map' "$FILE"; then
    cp "$FILE" "$FILE.bak-sets"

    # 72. Защита от null/undefined при вызове sets.map
    perl -pi -e 's/\bsets\.map\(/\(sets ?? []).map(/g' "$FILE"

    # 73. Убираем условия, из-за которых весь блок исчезает при пустом списке
    perl -pi -e 's/\{\s*sets\s*&&\s*sets\?\.length\s*>\s*0\s*&&/\{sets \&\&/g' "$FILE"
    perl -pi -e 's/\{\s*sets\s*&&\s*sets\.length\s*>\s*0\s*&&/\{sets \&\&/g' "$FILE"

    # 74. Если блок начинался только с проверки длины, оставляем его видимым
    perl -pi -e 's/\{\s*sets\.length\s*>\s*0\s*&&/\{/g' "$FILE"
    perl -pi -e 's/\{\s*sets\?\.length\s*>\s*0\s*&&/\{/g' "$FILE"

    # 75. Если перед map остался лишний guard вида {sets && ..., убираем его
    perl -pi -e 's/\{\s*sets\s*&&\s*\(sets \?\? \[\]\)\.map\(/\{(sets ?? []).map(/g' "$FILE"

    # 76. Добавляем видимое пустое состояние, если его ещё нет
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

# 77. Добавляем минимальный стиль для пустого состояния
CSS_FILE=$(find "$ROOT" -type f -name '*.css' -print | head -n 1 || true)

if [ -n "$CSS_FILE" ]; then
  if ! grep -qF '.empty-state' "$CSS_FILE"; then
    cat >> "$CSS_FILE" <<'CSS'

.empty-state {
  padding: 12px;
  border: 1px dashed #999;
  color: #666;
  border-radius: 8px;
}
CSS
    echo "CSS обновлён: $CSS_FILE"
  fi
fi

echo ""
echo "Готово."
echo "Проверь изменения: git diff"
echo "Резервные копии файлов имеют расширение .bak-sets"
