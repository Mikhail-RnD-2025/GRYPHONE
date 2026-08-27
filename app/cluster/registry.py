# -*- coding: utf-8 -*-
"""
app/cluster/registry.py
=======================
Реестр узлов кластера.

ЗАГОТОВКА: пока хранит один локальный узел. В будущем будет
поддерживать регистрацию нескольких узлов и проверку их живости.
"""
import logging
from typing import Dict, List, Optional

from app.cluster.models import Node, NodeRole

logger = logging.getLogger(__name__)


class NodeRegistry:
    """Реестр узлов кластера."""

    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._register_default()

    def _register_default(self) -> None:
        """Регистрирует локальный узел (пока всё на одном сервере)."""
        local = Node(
            id="local",
            role=NodeRole.CONTROL,
            host="127.0.0.1",
            port=5000,
            enabled=True,
            tags=["local", "all"],
        )
        self._nodes[local.id] = local
        logger.info("Зарегистрирован локальный узел: %s", local.id)

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def all_nodes(self) -> List[Node]:
        return list(self._nodes.values())

    def nodes_by_role(self, role: NodeRole) -> List[Node]:
        return [n for n in self._nodes.values() if n.role == role]

    def register(self, node: Node) -> None:
        self._nodes[node.id] = node
        logger.info("Зарегистрирован узел: %s (роль=%s)", node.id, node.role.value)

    def unregister(self, node_id: str) -> bool:
        if node_id in self._nodes:
            del self._nodes[node_id]
            return True
        return False


node_registry = NodeRegistry()
