# -*- coding: utf-8 -*-
"""
app/cluster/roles/base.py
=========================
Базовый класс обработчика роли узла.

ЗАГОТОВКА: каждая роль (control, capture, relay, recorder,
analytics) реализует этот интерфейс и определяет, какие модули
активируются на сервере с данной ролью.
"""
from typing import Optional


class NodeRoleHandler:
    """Базовый обработчик роли узла."""

    #: Роль из NodeRole, которую обрабатывает этот класс
    role: Optional[str] = None

    def setup(self, app) -> None:
        """Инициализация роли при старте узла."""
        raise NotImplementedError

    def teardown(self) -> None:
        """Очистка при остановке узла."""
        pass
