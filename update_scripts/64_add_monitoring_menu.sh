#!/bin/sh
# 64. update_scripts/64_add_monitoring_menu.sh
# 65. Добавляет пункт меню "Мониторинг", ведущий к наборам.
# 66. Запуск: ./64_add_monitoring_menu.sh [файл_меню]

set -eu

# 67. Определяем папку скрипта
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# 68. Ищем фронтенд рядом с папкой update_scripts
if [ -d "$SCRIPT_DIR/../frontend/src" ]; then
  DEFAULT_ROOT="$SCRIPT_DIR/../frontend/src"
else
  DEFAULT_ROOT="$PWD/frontend/src"
fi

# 69. Путь к фронтенду можно передать аргументом
ROOT="${1:-$DEFAULT_ROOT}"

# 70. Если первым аргументом передали конкретный файл меню, используем его
MENU_FILE=""
if [ $# -ge 1 ] && [ -f "$1" ]; then
  MENU_FILE="$1"
  ROOT=$(dirname "$MENU_FILE")
fi

LINK_TEXT="Мониторинг"

# 71. Проверяем наличие perl
if ! command -v perl >/dev/null 2>&1; then
  echo "Нужен perl. Например: sudo apt install perl" >&2
  exit 1
fi

# 72. Проверяем каталог фронтенда
if [ ! -e "$ROOT" ]; then
  echo "Не найден каталог фронтенда: $ROOT" >&2
  echo "Использование: $0 [файл_меню]" >&2
  exit 1
fi

echo "Добавляю пункт '$LINK_TEXT' в меню."
echo "Каталог поиска: $ROOT"

# 73. Определяем, есть ли уже роут /sets
ROUTER_TARGET="/#sets"
if grep -RqE --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=build 'path=[^>]*/sets' "$ROOT" 2>/dev/null; then
  ROUTER_TARGET="/sets"
fi

# 74. Позволяем переопределить цель через переменные окружения
ROUTER_TARGET="${MONITORING_TO:-$ROUTER_TARGET}"
PLAIN_HREF="${MONITORING_HREF:-#sets}"

echo "Цель перехода: $ROUTER_TARGET"

# 75. Добавляем якорь #sets там, где рендерятся наборы
find "$ROOT" \
  -type d \( -name node_modules -o -name dist -o -name build \) -prune \
  -o -type f \( -name '*.jsx' -o -name '*.js' -o -name '*.tsx' -o -name '*.ts' \) -print |
while read -r FILE; do
  if grep -qE 'sets(\?)?\.map' "$FILE"; then
    if ! grep -qF 'id="sets"' "$FILE"; then
      cp "$FILE" "$FILE.bak-anchor"

      # 76. Якорь перед списком наборов, если наборы уже защищены через ?? []
      perl -pi -e 's/\{\(sets \?\? \[\]\)\.map\(/\{<div id="sets"><\/div>\}\n\{(sets ?? []).map(/' "$FILE"

      # 77. Якорь перед обычным sets.map, если ещё не было ?? []
      perl -pi -e 's/\{sets\.map\(/\{<div id="sets"><\/div>\}\n\{sets.map(/' "$FILE"

      echo "Добавлен якорь #sets в: $FILE"
    fi
  fi
done

# 78. Ищем файл меню, если он не был указан явно
if [ -z "$MENU_FILE" ]; then
  MENU_FILE=$(find "$ROOT" \
    -type f \
    \( \
      -name '*Menu*.jsx' -o \
      -name '*Menu*.tsx' -o \
      -name '*Sidebar*.jsx' -o \
      -name '*Sidebar*.tsx' -o \
      -name '*Navbar*.jsx' -o \
      -name '*Navbar*.tsx' -o \
      -name '*Nav.jsx' -o \
      -name '*Nav.tsx' -o \
      -name '*Header*.jsx' -o \
      -name '*Header*.tsx' -o \
      -name 'App.jsx' -o \
      -name 'App.tsx' -o \
      -name 'Dashboard.jsx' -o \
      -name 'Dashboard.tsx' \
    \) -print | head -n 1 || true)
fi

# 79. Если по имени не нашли, ищем файлы с признаками меню
if [ -z "$MENU_FILE" ]; then
  MENU_FILE=$(find "$ROOT" \
    -type f \( -name '*.jsx' -o -name '*.tsx' \) \
    -exec grep -lE '<nav|NavLink|<ul|Menu|Sidebar|Navbar|Header' {} + | head -n 1 || true)
fi

if [ -z "$MENU_FILE" ]; then
  echo "Не удалось автоматически найти файл меню." >&2
  echo "Запусти скрипт с явным файлом, например:" >&2
  echo "$0 ../frontend/src/components/Dashboard.jsx" >&2
  exit 1
fi

echo "Файл меню: $MENU_FILE"

# 80. Если пункт уже есть, ничего не делаем
if grep -qF "$LINK_TEXT" "$MENU_FILE"; then
  echo "Пункт '$LINK_TEXT' уже есть в меню."
else
  cp "$MENU_FILE" "$MENU_FILE.bak-menu"

  # 81. Выбираем тип ссылки в зависимости от роутера
  if grep -qE 'NavLink|react-router-dom' "$MENU_FILE"; then
    LINK_TAG="<NavLink to=\"$ROUTER_TARGET\" className=\"nav-link monitoring-link\">$LINK_TEXT</NavLink>"
  elif grep -qE '<Link|react-router-dom' "$MENU_FILE"; then
    LINK_TAG="<Link to=\"$ROUTER_TARGET\" className=\"nav-link monitoring-link\">$LINK_TEXT</Link>"
  else
    LINK_TAG="<a href=\"$PLAIN_HREF\" className=\"menu-link monitoring-link\">$LINK_TEXT</a>"
  fi

  export LINK_TAG

  # 82. Пробуем вставить пункт перед </nav>
  if ! grep -qF "$LINK_TEXT" "$MENU_FILE" && grep -q '</nav>' "$MENU_FILE"; then
    perl -0777 -pi -e 's/(<\/nav>)/$ENV{LINK_TAG}\n$1/s' "$MENU_FILE"
  fi

  # 83. Если есть список <ul>, вставляем как <li>
  if ! grep -qF "$LINK_TEXT" "$MENU_FILE" && grep -q '</ul>' "$MENU_FILE"; then
    perl -0777 -pi -e 's/(<\/ul>)/<li>$ENV{LINK_TAG}<\/li>\n$1/s' "$MENU_FILE"
  fi

  # 84. Пробуем вставить перед </header>
  if ! grep -qF "$LINK_TEXT" "$MENU_FILE" && grep -q '</header>' "$MENU_FILE"; then
    perl -0777 -pi -e 's/(<\/header>)/$ENV{LINK_TAG}\n$1/s' "$MENU_FILE"
  fi

  # 85. Фолбек: вставляем в начало возвращаемого JSX
  if ! grep -qF "$LINK_TEXT" "$MENU_FILE"; then
    perl -0777 -pi -e 's/(return\s*\(\s*<>)/$1\n$ENV{LINK_TAG}/s' "$MENU_FILE"
  fi

  if ! grep -qF "$LINK_TEXT" "$MENU_FILE"; then
    perl -0777 -pi -e 's/(return\s*\(\s*<div[^>]*>)/$1\n$ENV{LINK_TAG}/s' "$MENU_FILE"
  fi

  if ! grep -qF "$LINK_TEXT" "$MENU_FILE"; then
    perl -0777 -pi -e 's/(return\s*\(\s*<[^>]*>)/$1\n$ENV{LINK_TAG}/s' "$MENU_FILE"
  fi

  if grep -qF "$LINK_TEXT" "$MENU_FILE"; then
    echo "Пункт '$LINK_TEXT' добавлен в: $MENU_FILE"
  else
    echo "Не удалось автоматически вставить пункт меню в: $MENU_FILE" >&2
    echo "Добавь вручную эту строку в меню:" >&2
    echo "$LINK_TAG" >&2
    exit 1
  fi
fi

# 86. Добавляем немного стилей для нового пункта
CSS_FILE=$(find "$ROOT" \
  -type d \( -name node_modules -o -name dist -o -name build \) -prune \
  -o -type f -name '*.css' -print | head -n 1 || true)

if [ -n "$CSS_FILE" ] && [ -w "$CSS_FILE" ]; then
  if ! grep -qF '.monitoring-link' "$CSS_FILE"; then
    {
      printf '%s\n' ''
      printf '%s\n' '.monitoring-link {'
      printf '%s\n' '  color: inherit;'
      printf '%s\n' '  text-decoration: none;'
      printf '%s\n' '  cursor: pointer;'
      printf '%s\n' '}'
      printf '%s\n' ''
      printf '%s\n' '.monitoring-link:hover {'
      printf '%s\n' '  opacity: 0.8;'
      printf '%s\n' '}'
    } >> "$CSS_FILE"

    echo "CSS обновлён: $CSS_FILE"
  fi
fi

echo ""
echo "Готово."
echo "Проверь изменения: git diff"
echo "Резервные копии: *.bak-menu и *.bak-anchor"