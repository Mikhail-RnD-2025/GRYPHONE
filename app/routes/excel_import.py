# -*- coding: utf-8 -*-
"""
app/routes/excel_import.py
==========================
API endpoint для импорта камер из Excel файла.

Endpoint:
  POST /api/cameras/import-excel

Request:
  multipart/form-data с полем "file" (Excel файл)

Response:
  {
    "success": true/false,
    "cameras_count": int,
    "sets_count": int,
    "message": str,
    "error": str (если success=false)
  }

Пример использования через fetch:
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  const response = await fetch('/api/cameras/import-excel', {
    method: 'POST',
    body: formData
  });

  const result = await response.json();
"""
import os
import tempfile
import logging
from pathlib import Path
from flask import request, jsonify
from app.services.camera_import_service import camera_import_service  # PATCH-215

logger = logging.getLogger(__name__)


def register(app):
    """Регистрирует роут импорта Excel в приложении."""

    @app.route("/api/cameras/import-excel", methods=["POST"])
    def import_cameras_excel():
        """PATCH-192: импорт через camera_import_service."""
        if "file" not in request.files:
            return jsonify({"success": False, "error": "Нет файла (поле file)"}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"success": False, "error": "Пустое имя файла"}), 400
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            return jsonify({"success": False, "error": "Нужен файл .xlsx или .xls"}), 400
        import tempfile
        import os
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        try:
            file.save(tmp.name)
            tmp.close()
            result = camera_import_service.import_from_excel(Path(tmp.name))
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result)
