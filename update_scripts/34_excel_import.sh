#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 34: ИМПОРТ КАМЕР ИЗ EXCEL
#  ------------------------------------------------------------
#  Что делает:
#    1. Создаёт Python-скрипт для импорта камер из Excel
#       (поддерживает .xlsx и .xls форматы)
#    2. Добавляет API endpoint /api/cameras/import-excel
#    3. Добавляет кнопку загрузки Excel в интерфейс редактора
#       наборов (SettingsPage.jsx)
#    4. Устанавливает библиотеку openpyxl если нужно
#
#  Запуск:   bash 34_excel_import.sh
#  После:    pip install openpyxl && bash build_frontend.sh
#            && python main.py
#
#  Использование:
#    1. Откройте Настройки → вкладка "Наборы"
#    2. Нажмите кнопку "📥 Импорт из Excel"
#    3. Выберите Excel файл (.xlsx или .xls)
#    4. Данные автоматически загрузятся в БД
#    5. Перезагрузите страницу (F5)
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo " Корень проекта: $PROJECT_DIR"

# ============================================================
# ЧАСТЬ 1: Python-скрипт для импорта из Excel
# ============================================================
cat > "$PROJECT_DIR/import_from_excel.py" << 'PYEOF_EXCEL'
# -*- coding: utf-8 -*-
"""
import_from_excel.py — импорт камер из Excel файла.

Поддерживаемые форматы:
  - .xlsx (Excel 2007+)
  - .xls (Excel 97-2003, требует xlrd)

Автоматически определяет колонки по заголовкам (регистронезависимо):
  Обязательные:
    - ID / id / идентификатор → id
    - Main URL / main_url / url / основной_url → main_url

  Опциональные:
    - Name / name / имя / название → name
    - Sub URL / sub_url / доп_url / дополнительный_url → sub_url
    - Enabled / enabled / включена / статус → enabled
    - Comment / comment / комментарий → comment
    - Audio / audio / звук / аудио → audio
    - Location / location / расположение / местоположение → location

Пример Excel таблицы:
┌─────┬──────────┬─────────────────────────────────────────────┐
│ ID  │ Name     │ main_url                       │ sub_url     │
├─────┼──────────────────────────────────────────┼─────────────┤
│ cam1│ Камера 1 │ rtsp://admin:pass@192.168...   │ rtsp://...  │
└─────┴──────────┴─────────────────────────────────────────────┘

Запуск через API: см. endpoint /api/cameras/import-excel
"""
import sys
import json
import sqlite3
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

try:
    import openpyxl
    from openpyxl import load_workbook
except ImportError:
    print("❌ Библиотека openpyxl не установлена!")
    print("   Установите: pip install openpyxl")
    sys.exit(1)

logger = logging.getLogger(__name__)

# Маппинг возможных названий колонок (нижний регистр)
COLUMN_MAPPING = {
    'id': ['id', 'идентификатор', 'id камеры', 'camera id', 'номер'],
    'name': ['name', 'имя', 'название', 'камера', 'camera name', 'название камеры'],
    'main_url': ['main_url', 'main url', 'основной_url', 'url', 'основной url',
                 'rtsp', 'ссылка', 'main', 'поток основной'],
    'sub_url': ['sub_url', 'sub url', 'дополнительный_url', 'субпоток', 'доп url',
                'дополнительный', 'sub', 'поток дополнительный'],
    'enabled': ['enabled', 'включена', 'статус', 'активна', 'enabled?', 'active', 'вкл'],
    'comment': ['comment', 'комментарий', 'описание', 'примечание', 'desc', 'note'],
    'audio': ['audio', 'звук', 'аудио', 'audio?', 'звук?', 'has audio'],
    'location': ['location', 'расположение', 'местоположение', 'адрес', 'place', 'где'],
}


def detect_columns(headers: List[str]) -> Tuple[Dict[str, int], List[str]]:
    """
    Определяет индексы колонок по заголовкам.

    Args:
        headers: Список заголовков колонок из Excel

    Returns:
        Tuple[Dict[str, int], List[str]]:
          - Dict: маппинг field_name -> column_index
          - List: список найденных полей для логирования
    """
    mapping = {}
    headers_lower = [h.strip().lower() if h else '' for h in headers]
    found_fields = []

    for field, possible_names in COLUMN_MAPPING.items():
        for idx, header in enumerate(headers_lower):
            if header in [name.lower() for name in possible_names]:
                mapping[field] = idx
                found_fields.append(f"{field} (колонка {idx+1}: '{headers[idx]}')")
                break

    return mapping, found_fields


def clean_value(value: Any) -> str:
    """
    Очищает значение от лишних пробелов и приводит к строке.

    Args:
        value: Любое значение из ячейки Excel

    Returns:
        str: Очищенная строка
    """
    if value is None:
        return ''
    return str(value).strip()


def parse_enabled(value: Any) -> bool:
    """
    Парсит значение enabled из разных форматов.

    Поддерживаемые форматы:
      - bool: True/False
      - int/float: 1/0, 1.0/0.0
      - str: "true"/"false", "да"/"нет", "yes"/"no", "вкл"/"выкл"

    Args:
        value: Значение из ячейки

    Returns:
        bool: True если камера включена
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)

    value_str = clean_value(value).lower()
    true_values = ['true', '1', 'да', 'yes', 'вкл', 'включена', 'активна', 'активен']
    return value_str in true_values


def parse_audio(value: Any) -> bool:
    """
    Парсит значение audio из разных форматов.

    По умолчанию возвращает True (аудио включено),
    если значение явно не указывает на False.

    Args:
        value: Значение из ячейки

    Returns:
        bool: True если аудио включено
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)

    value_str = clean_value(value).lower()
    false_values = ['false', '0', 'нет', 'no', 'выкл', 'отключена', 'без звука']
    return value_str not in false_values


def extract_ip(url: str) -> Optional[str]:
    """
    Извлекает IP-адрес из RTSP-ссылки.

    Примеры:
      rtsp://admin:pass@192.168.1.100:554/stream → 192.168.1.100
      rtsp://192.168.1.100:554/stream → 192.168.1.100

    Args:
        url: RTSP ссылка

    Returns:
        Optional[str]: IP-адрес или None
    """
    match = re.search(r'//(?:[^@]+@)?([^:/]+)', url or '')
    return match.group(1) if match else None


def read_excel_file(filepath: Path) -> Tuple[List[Dict[str, Any]], str]:
    """
    Читает Excel файл и возвращает список камер.

    Args:
        filepath: Путь к Excel файлу

    Returns:
        Tuple[List[Dict], str]:
          - List[Dict]: список камер
          - str: сообщение о результате (success/error)

    Raises:
        ValueError: Если файл невалиден или нет обязательных колонок
    """
    if not filepath.exists():
        raise ValueError(f"Файл не найден: {filepath}")

    print(f"📂 Чтение файла: {filepath}")

    try:
        # Загружаем workbook в режиме read_only для больших файлов
        wb = load_workbook(filepath, read_only=True, data_only=True)
        ws = wb.active

        if ws is None:
            raise ValueError("Не удалось прочитать активный лист")

        # Читаем заголовки (первая строка)
        headers = []
        for cell in next(ws.iter_rows(min_row=1, max_row=1)):
            headers.append(cell.value if cell.value is not None else '')

        print(f"📋 Заголовки колонок: {headers}")

        # Определяем маппинг колонок
        col_map, found_fields = detect_columns(headers)
        print(f"🔍 Определены колонки: {', '.join(found_fields)}")

        # Проверяем обязательные поля
        required = ['id', 'main_url']
        missing = [f for f in required if f not in col_map]
        if missing:
            raise ValueError(f"Не найдены обязательные колонки: {missing}. "
                           f"Найдены: {', '.join(found_fields)}")

        # Читаем данные
        cameras = []
        row_num = 1
        empty_rows = 0

        for row in ws.iter_rows(min_row=2):
            row_num += 1
            values = [cell.value for cell in row]

            # Пропускаем полностью пустые строки
            if not any(v is not None for v in values):
                empty_rows += 1
                continue

            try:
                # Извлекаем значения по маппингу
                id_idx = col_map['id']
                name_idx = col_map.get('name', id_idx)
                main_url_idx = col_map['main_url']
                sub_url_idx = col_map.get('sub_url', -1)
                enabled_idx = col_map.get('enabled', -1)
                comment_idx = col_map.get('comment', -1)
                audio_idx = col_map.get('audio', -1)
                location_idx = col_map.get('location', -1)

                camera = {
                    'id': clean_value(values[id_idx]),
                    'name': clean_value(values[name_idx]),
                    'main_url': clean_value(values[main_url_idx]),
                    'sub_url': clean_value(values[sub_url_idx]) if sub_url_idx >= 0 else '',
                    'enabled': parse_enabled(values[enabled_idx]) if enabled_idx >= 0 else True,
                    'comment': clean_value(values[comment_idx]) if comment_idx >= 0 else '',
                    'audio': parse_audio(values[audio_idx]) if audio_idx >= 0 else True,
                    'location': clean_value(values[location_idx]) if location_idx >= 0 else '',
                }

                # Пропускаем камеры без ID или URL
                if not camera['id'] or not camera['main_url']:
                    print(f"⚠️  Строка {row_num}: пропущена (нет ID или URL)")
                    continue

                # Если имя пустое, используем ID
                if not camera['name']:
                    camera['name'] = camera['id']

                cameras.append(camera)

            except Exception as e:
                print(f"️  Строка {row_num}: ошибка парсинга - {e}")
                continue

        wb.close()

        if not cameras:
            raise ValueError("Не найдено ни одной валидной камеры в файле")

        print(f"✅ Прочитано камер: {len(cameras)} (пропущено пустых строк: {empty_rows})")
        return cameras, "success"

    except Exception as e:
        raise ValueError(f"Ошибка чтения Excel файла: {e}")


def create_sets_from_cameras(cameras: List[Dict]) -> Dict:
    """
    Автоматически создаёт наборы на основе префиксов ID камер.

    Логика группировки:
      - ID вида "210-P-GAVw-001" → группа "210"
      - ID вида "301A-P-GAVw-001" → группа "301A"
      - Остальные → группа "other"

    Размеры сетки определяются автоматически:
      - 1-4 камеры: 2×2
      - 5-9 камер: 3×3
      - 10-16 камер: 4×4
      - и т.д.

    Args:
        cameras: Список камер

    Returns:
        Dict: структура наборов в формате sets.json
    """
    groups: Dict[str, List[str]] = {}

    for cam in cameras:
        cam_id = cam['id']
        # Определяем группу по префиксу (до первого дефиса)
        parts = cam_id.split('-')
        if len(parts) > 1:
            group = parts[0]
        else:
            group = 'other'

        if group not in groups:
            groups[group] = []
        groups[group].append(cam_id)

    # Создаём наборы
    sets_data = {
        'default_set': list(groups.keys())[0] if groups else '',
        'sets': {}
    }

    # Функция для расчёта размеров сетки
    def calculate_grid(count: int) -> Tuple[int, int]:
        if count <= 4:
            return 2, 2
        elif count <= 9:
            return 3, 3
        elif count <= 16:
            return 4, 4
        elif count <= 25:
            return 5, 5
        elif count <= 36:
            return 6, 6
        elif count <= 49:
            return 7, 7
        else:
            return 8, 8

    # Создаём наборы для каждой группы
    for group_id, cam_ids in groups.items():
        cols, rows = calculate_grid(len(cam_ids))
        sets_data['sets'][group_id] = {
            'name': f'📹 {group_id}',
            'camera_ids': cam_ids,
            'max_columns': cols,
            'max_rows': rows,
            'aspect_ratio': '16:9'
        }

    # Добавляем набор "Все камеры"
    sets_data['sets']['all'] = {
        'name': ' Все камеры',
        'camera_ids': [c['id'] for c in cameras],
        'max_columns': 8,
        'max_rows': 8,
        'aspect_ratio': '16:9'
    }
    sets_data['default_set'] = 'all'

    return sets_data


def save_to_database(cameras: List[Dict], sets_data: Dict,
                    db_path: Path = Path('rtsp_viewer.db')) -> None:
    """
    Сохраняет камеры и наборы в базу данных SQLite.

    Args:
        cameras: Список камер
        sets_data: Структура наборов
        db_path: Путь к SQLite базе данных
    """
    print(f"\n💾 Сохранение в БД: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Создаём таблицу settings, если её нет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    # Сохраняем камеры (перезаписываем существующие)
    cursor.execute(
        'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
        ('cameras', json.dumps(cameras, ensure_ascii=False, indent=2))
    )
    print(f"✅ Сохранено камер: {len(cameras)}")

    # Сохраняем наборы (перезаписываем существующие)
    cursor.execute(
        'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
        ('sets', json.dumps(sets_data, ensure_ascii=False, indent=2))
    )
    print(f"✅ Сохранено наборов: {len(sets_data['sets'])}")

    conn.commit()
    conn.close()


def print_statistics(cameras: List[Dict], sets_data: Dict) -> None:
    """
    Выводит подробную статистику импорта.

    Args:
        cameras: Список камер
        sets_data: Структура наборов
    """
    print("\n" + "="*70)
    print("📊 СТАТИСТИКА ИМПОРТА")
    print("="*70)

    # Статистика по камерам
    enabled_count = sum(1 for c in cameras if c['enabled'])
    with_audio = sum(1 for c in cameras if c['audio'])
    with_sub = sum(1 for c in cameras if c['sub_url'])
    with_location = sum(1 for c in cameras if c['location'])

    print(f"📹 Всего камер: {len(cameras)}")
    print(f"   ✅ Включено: {enabled_count}")
    print(f"   🔊 С аудио: {with_audio}")
    print(f"   🎥 С субпотоком: {with_sub}")
    print(f"   📍 С местоположением: {with_location}")

    # Статистика по IP
    ips: Dict[str, int] = {}
    for cam in cameras:
        ip = extract_ip(cam['main_url'])
        if ip:
            ips[ip] = ips.get(ip, 0) + 1

    print(f"\n Уникальных IP: {len(ips)}")
    if len(ips) <= 20:  # Показываем только если немного
        for ip, count in sorted(ips.items(), key=lambda x: -x[1])[:10]:
            print(f"   {ip}: {count} камер")

    # Статистика по наборам
    print(f"\n📦 Наборы:")
    for set_id, set_data in sets_data['sets'].items():
        cam_count = len(set_data['camera_ids'])
        grid = f"{set_data['max_columns']}×{set_data['max_rows']}"
        print(f"   {set_data['name']}: {cam_count} камер (сетка {grid})")

    print("="*70)


def import_excel(filepath: str, db_path: str = 'rtsp_viewer.db') -> Dict:
    """
    Главная функция импорта Excel файла.

    Args:
        filepath: Путь к Excel файлу
        db_path: Путь к SQLite базе данных

    Returns:
        Dict: Результат импорта со статистикой
    """
    try:
        # Читаем Excel
        cameras, status = read_excel_file(Path(filepath))

        # Создаём наборы
        sets_data = create_sets_from_cameras(cameras)

        # Выводим статистику
        print_statistics(cameras, sets_data)

        # Сохраняем в БД
        save_to_database(cameras, sets_data, Path(db_path))

        print("\n✅ Импорт завершён успешно!")

        return {
            'success': True,
            'cameras_count': len(cameras),
            'sets_count': len(sets_data['sets']),
            'message': f"Импортировано {len(cameras)} камер в {len(sets_data['sets'])} наборов"
        }

    except Exception as e:
        error_msg = f"❌ Ошибка импорта: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'message': error_msg
        }


# CLI интерфейс
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python import_from_excel.py <файл.xlsx> [db_path]")
        print("\nПоддерживаемые форматы: .xlsx, .xls")
        print("\nПример:")
        print("  python import_from_excel.py cameras.xlsx")
        print("  python import_from_excel.py cameras.xlsx rtsp_viewer.db")
        sys.exit(1)

    filepath = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else 'rtsp_viewer.db'

    result = import_excel(filepath, db_path)

    if not result['success']:
        sys.exit(1)
PYEOF_EXCEL
echo "  ✔ import_from_excel.py (скрипт импорта)"

# ============================================================
# ЧАСТЬ 2: API endpoint для загрузки Excel
# ============================================================
cat > "$PROJECT_DIR/app/routes/excel_import.py" << 'PYEOF_API'
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

            db_path = Path(app.config.get('DB_PATH', 'rtsp_viewer.db'))
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
PYEOF_API
echo "  ✔ app/routes/excel_import.py (API endpoint)"

# ============================================================
# ЧАСТЬ 3: Обновление app/routes/__init__.py
# ============================================================
cat > "$PROJECT_DIR/app/routes/__init__.py" << 'PYEOF_ROUTES_INIT'
# -*- coding: utf-8 -*-
"""
app/routes/__init__.py
======================
Регистрация всех роутов приложения.

Модули:
  - api            : основные API endpoints
  - stream         : SSE stream статусов
  - hls            : раздача HLS сегментов
  - excel_import   : импорт камер из Excel (НОВОЕ в v34)
"""
from app.routes import api, stream, hls, excel_import


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
PYEOF_ROUTES_INIT
echo "  ✔ app/routes/__init__.py (добавлен excel_import)"

# ============================================================
# ЧАСТЬ 4: Frontend - кнопка загрузки в SettingsPage.jsx
# ============================================================
cat > "$PROJECT_DIR/frontend/src/pages/SettingsPage.jsx" << 'JSXEOF'
// ============================================================
//  GRYPHONE — страница настроек
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v34):
//  • Добавлена кнопка "📥 Импорт из Excel" во вкладку "Наборы"
//  • При загрузке файла автоматически отправляется на сервер
//  • Показываются уведомления о результате импорта
// ============================================================
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import Header from '../components/Header'
import Toasts from '../components/Toasts'
import { getSets, saveSets, getConfig, saveConfig } from '../api'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('sets')
  const [setsData, setSetsData] = useState(null)
  const [configData, setConfigData] = useState(null)
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const sets = await getSets()
      setSetsData(sets)
      const config = await getConfig()
      setConfigData(config)
    } catch (e) {
      console.error('Ошибка загрузки данных:', e)
    }
  }

  // ИСПРАВЛЕНО (v34): обработчик загрузки Excel файла
  const handleExcelImport = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    // Проверяем тип файла
    const validTypes = [
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ]
    if (!validTypes.includes(file.type) && !file.name.endsWith('.xls') && !file.name.endsWith('.xlsx')) {
      if (window.addToast) {
        window.addToast(' Неверный формат файла. Используйте .xlsx или .xls', 'error')
      }
      return
    }

    setImporting(true)

    try {
      // Создаём FormData для загрузки файла
      const formData = new FormData()
      formData.append('file', file)

      // Отправляем на сервер
      const response = await fetch('/api/cameras/import-excel', {
        method: 'POST',
        body: formData,
      })

      const result = await response.json()

      if (result.success) {
        if (window.addToast) {
          window.addToast(
            `✅ ${result.message}. Перезагрузите страницу (F5)`,
            'success'
          )
        }
        // Перезагружаем данные
        await loadData()
      } else {
        if (window.addToast) {
          window.addToast(`❌ ${result.message}`, 'error')
        }
      }
    } catch (e) {
      console.error('Ошибка импорта:', e)
      if (window.addToast) {
        window.addToast(`❌ Ошибка импорта: ${e.message}`, 'error')
      }
    } finally {
      setImporting(false)
      // Очищаем input file
      event.target.value = ''
    }
  }

  const handleSaveSets = async () => {
    try {
      await saveSets(setsData)
      if (window.addToast) {
        window.addToast('✅ Наборы сохранены', 'success')
      }
    } catch (e) {
      console.error('Ошибка сохранения:', e)
      if (window.addToast) {
        window.addToast('❌ Ошибка сохранения наборов', 'error')
      }
    }
  }

  return (
    <div className="page">
      <Header />

      <h1 className="page-title">Настройки</h1>

      {/* Вкладки */}
      <div className="tabs">
        <button
          className={`btn ${activeTab === 'sets' ? 'btn-primary' : ''}`}
          onClick={() => setActiveTab('sets')}
        >
          📦 Наборы
        </button>
        <button
          className={`btn ${activeTab === 'config' ? 'btn-primary' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          ⚙️ Конфигурация
        </button>
        <Link to="/" className="btn">
          ← Назад к камерам
        </Link>
      </div>

      {/* Вкладка "Наборы" */}
      {activeTab === 'sets' && (
        <div className="tab-content">
          <h2>Управление наборами камер</h2>

          {/* ИСПРАВЛЕНО (v34): кнопка импорта из Excel */}
          <div style={{
            marginBottom: '20px',
            padding: '16px',
            background: '#1e293b',
            borderRadius: '8px',
            border: '1px solid #334155'
          }}>
            <h3 style={{ marginBottom: '12px' }}>📥 Импорт из Excel</h3>
            <p style={{ color: '#94a3b8', marginBottom: '12px' }}>
              Загрузите Excel файл с камерами. Файл должен содержать колонки:
              <br />
              <strong>ID</strong> (обязательно), <strong>main_url</strong> (обязательно),
              name, sub_url, enabled, comment, audio, location
            </p>

            <label className="btn btn-primary" style={{ cursor: 'pointer' }}>
              {importing ? '⏳ Загрузка...' : ' Выбрать Excel файл'}
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleExcelImport}
                disabled={importing}
                style={{ display: 'none' }}
              />
            </label>

            <div style={{
              marginTop: '12px',
              fontSize: '0.75rem',
              color: '#64748b'
            }}>
              Поддерживаются форматы: .xlsx (Excel 2007+), .xls (Excel 97-2003)
            </div>
          </div>

          {setsData ? (
            <div>
              <p>Активный набор: <strong>{setsData.default_set || 'не выбран'}</strong></p>
              <p>Всего наборов: <strong>{Object.keys(setsData.sets || {}).length}</strong></p>
              <button className="btn btn-primary" onClick={handleSaveSets}>
                💾 Сохранить наборы
              </button>
            </div>
          ) : (
            <p>Загрузка...</p>
          )}
        </div>
      )}

      {/* Вкладка "Конфигурация" */}
      {activeTab === 'config' && (
        <div className="tab-content">
          <h2>Конфигурация системы</h2>
          {configData ? (
            <pre style={{
              background: '#0b0d10',
              padding: '16px',
              borderRadius: '8px',
              overflow: 'auto',
              fontSize: '0.875rem'
            }}>
              {JSON.stringify(configData, null, 2)}
            </pre>
          ) : (
            <p>Загрузка...</p>
          )}
        </div>
      )}

      <Toasts />
    </div>
  )
}
JSXEOF
echo "  ✔ frontend/src/pages/SettingsPage.jsx (кнопка импорта)"

# ============================================================
# ЧАСТЬ 5: Инструкция по установке зависимостей
# ============================================================
cat > "$PROJECT_DIR/INSTALL_EXCEL_IMPORT.md" << 'MDEOF'
# 📦 Установка импорта из Excel

## Требования

Python 3.7+ и библиотека `openpyxl` для работы с Excel файлами.

## Установка

### Вариант 1: Автоматическая (рекомендуется)

```bash
pip install openpyxl