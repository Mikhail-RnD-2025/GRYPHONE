# -*- coding: utf-8 -*-
"""
app/core/node.py
================
Идентификация текущего узла.

ЗАГОТОВКА: определяет, какой узел и с какой ролью запущен в
этом процессе. Позже будет читаться из конфигурации кластера
или аргументов командной строки (например, --role capture).
"""
import os
from typing import Optional


def current_node_id() -> str:
    """Идентификатор текущего узла (по умолчанию 'local')."""
    return os.environ.get("GRYPHONE_NODE_ID", "local")


def current_role() -> Optional[str]:
    """Роль текущего узла (пока не задана — единый сервер)."""
    return os.environ.get("GRYPHONE_NODE_ROLE")
