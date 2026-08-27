# -*- coding: utf-8 -*-
"""
app/cluster/messaging/bus.py
============================
Шина событий кластера.

ЗАГОТОВКА: сейчас шина внутрипроцессная (pub/sub в памяти).
В будущем транспорт можно заменить на сетевой (очередь, HTTP),
не меняя подписчиков.

Это та же событийная шина, что используется для развязки модулей:
  - модули публикуют события (камера включена, поток потерян)
  - заинтересованные узлы/модули подписываются
"""
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class EventBus:
    """Простая шина событий (publish / subscribe)."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(payload)
            except Exception as e:  # noqa: BLE001
                logger.error("Ошибка обработчика события %s: %s", event_type, e)


cluster_bus = EventBus()
