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
