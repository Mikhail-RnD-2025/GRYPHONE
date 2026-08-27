# -*- coding: utf-8 -*-
"""
app/routes/__init__.py
======================
Регистрация всех роутов приложения.

Модули:
  - api            : основные API endpoints
  - stream         : SSE stream статусов
  - hls            : раздача HLS сегментов
  - excel_import   : импорт камер из Excel
  - dashboard      : улучшенный дашборд (НОВОЕ в v36)
"""
from app.routes import api, stream, hls, excel_import, dashboard


def register_routes(app):
    """
    Регистрирует все роуты в Flask приложении.

    Args:
        app: Flask application instance
    """
    api.register(app)
    stream.register(app)
    hls.register(app)
    excel_import.register(app)
    dashboard.register(app)
