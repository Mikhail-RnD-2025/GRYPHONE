#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 13: ТОЧКА ВХОДА И ФАБРИКА ПРИЛОЖЕНИЯ
#  ------------------------------------------------------------
#  Заполняет:
#    - main.py            — точка входа бэкенда
#    - app/__init__.py    — фабрика приложения (создаёт приложение,
#                           регистрирует роуты, запускает воркеры)
#
#  Запуск:   bash 13_main.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ============================================================
# app/__init__.py — фабрика приложения
# ============================================================
cat > "$PROJECT_DIR/app/__init__.py" << 'PYEOF_FACTORY'
# -*- coding: utf-8 -*-
"""
app/__init__.py
===============
Фабрика приложения: создаёт экземпляр веб-фреймворка, регистрирует
роуты и запускает фоновые задачи (менеджер стримера, очистка кэша).

Использование:
    from app import create_app
    app = create_app()
    app.run()
"""
import logging
import threading
from flask import Flask

from app.config import config
from app.services.stream_manager import stream_manager
from app.workers.cleanup_worker import cleanup_worker
from app.routes import register_routes

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Создаёт и настраивает приложение.

    Возвращает настроенный экземпляр приложения, готовый к запуску.
    """
    app = Flask(__name__)

    # Настраиваем логирование.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Регистрируем роуты.
    register_routes(app)

    # Запускаем менеджер стримера (асинхронный цикл в отдельном потоке).
    stream_manager.start()

    # Запускаем фоновую задачу очистки кэша.
    cleanup_thread = threading.Thread(
        target=cleanup_worker, daemon=True, name="CleanupWorker"
    )
    cleanup_thread.start()

    logger.info("✅ Приложение создано и настроено")
    return app
PYEOF_FACTORY
echo "  ✔ app/__init__.py"

# ============================================================
# main.py — точка входа бэкенда
# ============================================================
cat > "$PROJECT_DIR/main.py" << 'PYEOF_MAIN'
# -*- coding: utf-8 -*-
"""
main.py
=======
Точка входа бэкенда.

Создаёт приложение с помощью фабрики и запускает веб-сервер.
Параметры сервера (хост, порт) берутся из конфигурации.

Запуск:
    python main.py
"""
import logging

from app import create_app
from app.config import config

logger = logging.getLogger(__name__)


def main():
    """Главная функция: создаёт и запускает приложение."""
    # Создаём приложение.
    app = create_app()

    # Берём параметры сервера из конфигурации.
    host = config.get("server", "host", default="0.0.0.0")
    port = config.get("server", "port", default=5000)

    logger.info("🚀 Запуск сервера на %s:%s", host, port)

    # Запускаем веб-сервер.
    # Отключаем перезагрузчик, чтобы не дублировать фоновые задачи.
    app.run(host=host, port=port, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
PYEOF_MAIN
echo "  ✔ main.py"

# ------------------------------------------------------------
# Проверка, что файлы созданы и не пусты
# ------------------------------------------------------------
for f in app/__init__.py main.py; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
done

echo "✅ Точка входа и фабрика приложения готовы (с правильным синтаксисом)."
echo "ℹ️  Запускалка всех скриптов — скрипт 14."