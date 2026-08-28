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

logger = logging.getLogger(__name__)


def register(app):
    """Регистрирует роут импорта Excel в приложении."""

    @app.route("/api/cameras/import-excel", methods=["POST"])
    def import_excel():
        """
        Импортирует камеры из загруженного Excel файла.

        Поддерживаемые форматы: .xlsx, .xls
        Файл временно сохраняется, обрабатывается и удаляется.
        """
        # Проверяем наличие файла
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Файл не загружен',
                'message': 'В запросе отсутствует поле "file"'
            }), 400

        file = request.files['file']

        # Проверяем имя файла
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Файл не выбран',
                'message': 'Имя файла пустое'
            }), 400

        # Проверяем расширение
        filename = file.filename.lower()
        if not (filename.endswith('.xlsx') or filename.endswith('.xls')):
            return jsonify({
                'success': False,
                'error': 'Неверный формат файла',
                'message': 'Поддерживаются только файлы .xlsx или .xls'
            }), 400

        try:
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.xlsx' if filename.endswith('.xlsx') else '.xls'
            ) as tmp_file:
                tmp_path = tmp_file.name
                file.save(tmp_path)

            logger.info(f"📁 Загружен файл: {file.filename} → {tmp_path}")

            # Импортируем через import_from_excel
            from import_from_excel import import_excel as import_func

            db_path = Path(app.config.get('DB_PATH', str(DATABASE_PATH)))
            result = import_func(tmp_path, str(db_path))

            return jsonify(result)

        except Exception as e:
            logger.error(f"❌ Ошибка импорта Excel: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
                'message': f'Ошибка при обработке файла: {e}'
            }), 500

        finally:
            # Удаляем временный файл
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                    logger.info(f"🗑️ Временный файл удалён: {tmp_path}")
                except Exception as e:
                    logger.warning(f"⚠️  Не удалось удалить временный файл: {e}")
