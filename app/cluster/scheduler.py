# -*- coding: utf-8 -*-
"""
app/cluster/scheduler.py
========================
Распределение камер по узлам захвата.

ЗАГОТОВКА: пока все камеры назначаются на локальный узел.
В будущем будет балансировать нагрузку между несколькими
capture-узлами.
"""
import logging
from typing import Dict, List, Optional

from app.cluster.models import CameraAssignment

logger = logging.getLogger(__name__)


class CameraScheduler:
    """Распределяет камеры по узлам захвата."""

    def __init__(self):
        self._assignments: Dict[str, CameraAssignment] = {}

    def assign_all(self, camera_ids: List[str], node_id: str = "local") -> None:
        """Назначает все камеры на указанный узел."""
        for cam_id in camera_ids:
            self._assignments[cam_id] = CameraAssignment(
                camera_id=cam_id,
                node_id=node_id,
            )
        logger.info("Назначено %d камер на узел %s", len(camera_ids), node_id)

    def get_assignment(self, camera_id: str) -> Optional[CameraAssignment]:
        return self._assignments.get(camera_id)

    def cameras_on_node(self, node_id: str) -> List[str]:
        return [
            a.camera_id for a in self._assignments.values()
            if a.node_id == node_id
        ]


camera_scheduler = CameraScheduler()
