#!/usr/bin/env python3
"""
193. update_scripts/193_merge_logic_and_fix.py
"""

import sys
from pathlib import Path


def find_project_root():
    p = Path.cwd()
    while True:
        if (p / "frontend").is_dir() and (p / "update_scripts").is_dir():
            return p
        parent = p.parent
        if parent == p:
            print("[FAIL] Не найден корень проекта")
            sys.exit(1)
        p = parent


MERGE_IMPORT_JSON = '''    def import_from_json(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Импортирует камеры из JSON массива (МЕРЖ: обновление + добавление)."""
        try:
            current_cams = {c.id: c.to_dict() for c in self.camera_service.all_cameras()}
            updated = 0
            added = 0
            errors = []

            for i, cam_data in enumerate(data):
                try:
                    # Парсим полные RTSP URL
                    if cam_data.get('main_url') and cam_data['main_url'].strip().lower().startswith('rtsp://'):
                        parsed = parse_rtsp_url(cam_data['main_url'])
                        if parsed:
                            if not cam_data.get('login'):
                                cam_data['login'] = parsed['login']
                            if not cam_data.get('pass'):
                                cam_data['pass'] = parsed['pass']
                            if not cam_data.get('ipaddress'):
                                cam_data['ipaddress'] = parsed['ipaddress']
                            if not cam_data.get('port') or cam_data.get('port') == '554':
                                cam_data['port'] = parsed['port']
                            cam_data['main_url'] = parsed['path']

                    cam_id = cam_data.get('id')
                    if not cam_id or not cam_data.get('ipaddress') or not cam_data.get('main_url'):
                        errors.append(f"Камера {i}: пропущена (нет ID/IP/main_url)")
                        continue

                    if cam_id in current_cams:
                        current_cams[cam_id].update(cam_data)
                        updated += 1
                    else:
                        current_cams[cam_id] = cam_data
                        added += 1

                except Exception as e:
                    errors.append(f"Камера {i}: ошибка - {str(e)}")
                    continue

            all_cams = list(current_cams.values())
            if not all_cams:
                return {'success': False, 'error': 'Не найдено валидных камер', 'errors': errors}

            self.camera_service.save_cameras(all_cams)

            return {
                'success': True,
                'imported': len(all_cams),
                'updated': updated,
                'added': added,
                'errors': errors
            }

        except Exception as e:
            return {'success': False, 'error': f'Ошибка импорта: {str(e)}'}
'''

MERGE_EXCEL_BLOCK = '''            if not cameras:
                return {'success': False, 'error': 'Не найдено валидных камер в файле', 'errors': errors}

            # PATCH-193: МЕРЖ — обновление существующих + добавление новых
            current_cams = {c.id: c.to_dict() for c in self.camera_service.all_cameras()}
            updated = 0
            added = 0
            for new_cam in cameras:
                cam_id = new_cam.get('id')
                if cam_id in current_cams:
                    current_cams[cam_id].update(new_cam)
                    updated += 1
                else:
                    current_cams[cam_id] = new_cam
                    added += 1

            all_cams = list(current_cams.values())
            self.camera_service.save_cameras(all_cams)

            return {
                'success': True,
                'imported': len(all_cams),
                'updated': updated,
                'added': added,
                'skipped': skipped_rows,
                'errors': errors
            }'''

FIX_EXPORT = '''    def export_to_excel(self, file_path: Path) -> Dict[str, Any]:
        """Экспортирует камеры в Excel файл."""
        try:
            import openpyxl
        except ImportError:
            return {'success': False, 'error': 'openpyxl не установлен'}

        try:
            cameras = self.camera_service.all_cameras()

            # PATCH-193: проверка пустого списка
            if not cameras:
                logger.warning("export_to_excel: список камер пуст")
                # всё равно создаём файл с заголовками
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Камеры"
                headers = ['ID', 'Имя', 'Login', 'Пароль', 'IP-адрес', 'Порт',
                          'Путь основного потока', 'Путь субпотока', 'Путь sub2',
                          'Включена', 'Комментарий', 'Аудио', 'Местоположение']
                ws.append(headers)
                wb.save(file_path)
                wb.close()
                return {'success': True, 'exported': 0, 'warning': 'Список камер пуст'}

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Камеры"

            headers = ['ID', 'Имя', 'Login', 'Пароль', 'IP-адрес', 'Порт',
                      'Путь основного потока', 'Путь субпотока', 'Путь sub2',
                      'Включена', 'Комментарий', 'Аудио', 'Местоположение']
            ws.append(headers)

            for cam in cameras:
                ws.append([
                    cam.id, cam.name, cam.login, cam.pass_, cam.ipaddress, cam.port,
                    cam.main_url, cam.sub_url, cam.sub2_url,
                    cam.enabled, cam.comment, cam.audio, cam.location
                ])

            wb.save(file_path)
            wb.close()
            return {'success': True, 'exported': len(cameras)}

        except Exception as e:
            return {'success': False, 'error': f'Ошибка экспорта: {str(e)}'}
'''

FIX_API = '''    @app.route("/api/cameras/import-json", methods=["POST"])
    def import_cameras_json():
        """Импорт камер из JSON-массива."""
        data = request.get_json(silent=True)
        if data is None:
            # PATCH-193: fallback парсинг (для Windows CMD)
            try:
                import json as _json
                raw = request.get_data(as_text=True)
                data = _json.loads(raw)
            except Exception as e:
                logger.error(f"Не удалось распарсить JSON: {e}")
                return jsonify({"success": False, "error": f"Не удалось распарсить JSON: {e}"}), 400
        if not isinstance(data, list):
            return jsonify({"success": False, "error": "Ожидается JSON-массив камер"}), 400
        result = camera_import_service.import_from_json(data)
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result)
'''


def main():
    root = find_project_root()
    print("=" * 76)
    print("193: мерж-логика + фиксы")
    print("=" * 76)
    print()

    # 1. Восстановление камер из БД
    print("--- Восстановление камер ---")
    try:
        from app.services.camera_service import camera_service
        camera_service.reload()
        n = len(camera_service.all_cameras())
        print(f"  [OK] Камер в памяти: {n}")
    except Exception as e:
        print(f"  [WARN] {e}")

    # 2. Патч camera_import_service.py
    print()
    print("--- camera_import_service.py ---")
    svc = root / "app" / "services" / "camera_import_service.py"
    b = svc.with_suffix(".py.bak-193")
    b.write_text(svc.read_text(encoding="utf-8"), encoding="utf-8")
    c = svc.read_text(encoding="utf-8")
    n = 0

    # import_from_json → merge
    old = '    def import_from_json(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:'
    if old in c:
        start = c.find(old)
        # найти конец функции: следующий метод с таким же отступом
        end_marker = "\n    def export_to_json"
        end = c.find(end_marker, start)
        if end != -1:
            c = c[:start] + MERGE_IMPORT_JSON + c[end:]
            n += 1
            print("  [OK] import_from_json: merge logic")

    # import_from_excel: часть с сохранением → merge
    old_save = """            if not cameras:
                return {'success': False, 'error': 'Не найдено валидных камер в файле', 'errors': errors}

            # Сохраняем через camera_service
            self.camera_service.save_cameras(cameras)

            return {
                'success': True,
                'imported': len(cameras),
                'skipped': skipped_rows,
                'errors': errors
            }"""
    if old_save in c:
        c = c.replace(old_save, MERGE_EXCEL_BLOCK, 1)
        n += 1
        print("  [OK] import_from_excel: merge logic")

    # export_to_excel: полный блок
    old_export_start = '    def export_to_excel(self, file_path: Path) -> Dict[str, Any]:'
    old_export_end = "\n    def import_from_json"
    start = c.find(old_export_start)
    end = c.find(old_export_end, start)
    if start != -1 and end != -1:
        c = c[:start] + FIX_EXPORT + c[end:]
        n += 1
        print("  [OK] export_to_excel: пустой список")

    if n == 3:
        try:
            compile(c, str(svc), "exec")
            svc.write_text(c, encoding="utf-8")
            print("  [OK] Сохранено")
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            svc.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)
    else:
        print(f"  [FAIL] {n}/3 — откат")
        svc.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # 3. Патч api.py
    print()
    print("--- api.py ---")
    api = root / "app" / "routes" / "api.py"
    c = api.read_text(encoding="utf-8")
    old_api = '''    @app.route("/api/cameras/import-json", methods=["POST"])
    def import_cameras_json():
        \"\"\"Импорт камер из JSON-массива.\"\"\"
        data = request.get_json(silent=True)
        if not isinstance(data, list):
            return jsonify({"success": False, "error": "Ожидается JSON-массив камер"}), 400
        result = camera_import_service.import_from_json(data)
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result)'''
    if old_api in c:
        c = c.replace(old_api, FIX_API, 1)
        try:
            compile(c, str(api), "exec")
            api.write_text(c, encoding="utf-8")
            print("  [OK] import-json: fallback парсинг")
        except SyntaxError as e:
            print(f"  [FAIL] {e}")
            sys.exit(1)
    else:
        print("  [FAIL] якорь не найден")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Перезапустите сервер:")
    print("  python main.py")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix: merge logic in import + restore cameras (PATCH-193)" \\')
    print('  -m "import_from_json/excel: merge (update existing + add new)" \\')
    print('  -m "export_to_excel: check empty list before write" \\')
    print('  -m "api import-json: fallback JSON parsing for Windows CMD" \\')
    print('  -m "camera_service.reload() restores cameras from DB"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()