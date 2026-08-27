#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 15: ОДИН ПОРТ (исправлено)
#  ------------------------------------------------------------
#  ИСПРАВЛЕНО: убрано создание 01_meta.sh через вложенный
#  heredoc, которое вызывало ошибку.
#
#  Что делает:
#    1. Обновляет app/__init__.py: раздача фронтенда из фронтенд/дист
#    2. Удаляет app/routes/pages.py (если есть)
#    3. Обновляет app/routes/__init__.py: без регистрации pages
#    4. Создаёт build_frontend.sh для сборки фронтенда
#
#  Запуск:   bash 15_single_port.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# 1. app/__init__.py — фабрика с раздачей фронтенда
# ============================================================
cat > "$PROJECT_DIR/app/__init__.py" << 'PYEOF_FACTORY'
# -*- coding: utf-8 -*-
"""
app/__init__.py
===============
Фабрика приложения: создаёт веб-фреймворк, регистрирует роуты, раздаёт
собранный фронтенд из фронтенд/дист и запускает фоновые задачи.
"""
import logging
import threading
from pathlib import Path
from flask import Flask, send_from_directory, abort

from app.config import config
from app.services.stream_manager import stream_manager
from app.services.camera_service import camera_service
from app.workers.cleanup_worker import cleanup_worker
from app.routes import register_routes

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Создаёт и настраивает приложение."""
    project_root = Path(__file__).parent.parent
    frontend_dist = project_root / "frontend" / "dist"

    app = Flask(__name__, static_folder=None)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    _register_frontend(app, frontend_dist)
    register_routes(app)

    stream_manager.start()
    stream_manager.sync(camera_service.enabled_cameras())

    cleanup_thread = threading.Thread(
        target=cleanup_worker, daemon=True, name="CleanupWorker"
    )
    cleanup_thread.start()

    logger.info("✅ Приложение создано и настроено")
    return app


def _register_frontend(app: Flask, dist_dir: Path) -> None:
    """Регистрирует раздачу собранного фронтенда + фоллбэк."""

    @app.route("/")
    def index():
        """Главная страница."""
        if not (dist_dir / "index.html").is_file():
            return (
                "<h3>Фронтенд не собран</h3>"
                "<p>Выполните: <code>bash build_frontend.sh</code></p>",
                503,
            )
        return send_from_directory(str(dist_dir), "index.html")

    @app.route("/assets/<path:filename>")
    def assets(filename):
        """Отдаёт ассеты фронтенда."""
        assets_dir = dist_dir / "assets"
        if not assets_dir.is_dir():
            abort(404)
        return send_from_directory(str(assets_dir), filename)

    @app.route("/<path:filename>")
    def static_files(filename):
        """Отдаёт статические файлы и фоллбэк для одностраничника."""
        file_path = dist_dir / filename
        if file_path.is_file():
            return send_from_directory(str(dist_dir), filename)
        index_path = dist_dir / "index.html"
        if not index_path.is_file():
            abort(404)
        return send_from_directory(str(dist_dir), "index.html")
PYEOF_FACTORY
echo "  ✔ app/__init__.py (раздача фронтенда)"

# ============================================================
# 2. Удаляем app/routes/pages.py (если существует)
# ============================================================
if [ -f "$PROJECT_DIR/app/routes/pages.py" ]; then
  rm -f "$PROJECT_DIR/app/routes/pages.py"
  echo "  ✔ Удалён app/routes/pages.py"
else
  echo "  ⏭ app/routes/pages.py уже отсутствует"
fi

# ============================================================
# 3. app/routes/__init__.py — без регистрации pages
# ============================================================
cat > "$PROJECT_DIR/app/routes/__init__.py" << 'PYEOF_ROUTES'
# -*- coding: utf-8 -*-
"""
Пакет роутов приложения.

Модули:
  - api    : роуты /api/*
  - stream : роуты событий и логов
  - hls    : роуты /hls/*

Корневой адрес и раздачу статики обрабатывает app/__init__.py.
"""
from app.routes import api, stream, hls


def register_routes(app):
    """Регистрирует все роуты в приложении."""
    api.register(app)
    stream.register(app)
    hls.register(app)
PYEOF_ROUTES
echo "  ✔ app/routes/__init__.py (без pages)"

# ============================================================
# 4. build_frontend.sh — обёртка для сборки фронтенда
# ============================================================
cat > "$PROJECT_DIR/build_frontend.sh" << 'BUILDEOF'
#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — сборка фронтенда
#  ------------------------------------------------------------
#  Запускает установку зависимостей и сборку фронтенда.
#  После этого веб-фреймворк раздаст собранный фронтенд
#  из фронтенд/дист на порту 5000 (один порт).
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "📁 Каталог фронтенда: $FRONTEND_DIR"

if [ ! -d "$FRONTEND_DIR" ]; then
  echo "❌ ОШИБКА: папка фронтенд не найдена!" >&2
  exit 1
fi

cd "$FRONTEND_DIR"

# Устанавливаем зависимости (если нужно).
if [ ! -d "node_modules" ]; then
  echo "📦 Установка зависимостей..."
  npm install
fi

# Собираем фронтенд.
echo "🔨 Сборка фронтенда..."
npm run build

if [ -d "dist" ] && [ -f "dist/index.html" ]; then
  echo "✅ Сборка успешна: фронтенд/дист"
  echo ""
  echo "Теперь запустите бэкенд:"
  echo "  cd .. && python main.py"
  echo ""
  echo "Откройте: http://localhost:5000"
else
  echo "❌ ОШИБКА: фронтенд/дист не создан!" >&2
  exit 1
fi
BUILDEOF
chmod +x "$PROJECT_DIR/build_frontend.sh" 2>/dev/null || true
echo "  ✔ build_frontend.sh"

# ------------------------------------------------------------
# Проверка
# ------------------------------------------------------------
for f in app/__init__.py app/routes/__init__.py build_frontend.sh; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Все изменения применены"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что дальше:"
echo "  1. Соберите фронтенд:"
echo "       bash build_frontend.sh"
echo ""
echo "  2. Запустите бэкенд:"
echo "       python main.py"
echo ""
echo "  3. Откройте: http://localhost:5000"