#!/usr/bin/env python3
"""
192. update_scripts/192_indent_fix_and_excel_route.py
----------------------------------------------------------------------------
  • api.py: убирает блок PATCH-191 с нулевым отступом, добавляет ВНУТРЬ
    register(app) только export-excel / import-json / export-json
    (import-excel уже есть в excel_import.py — не дублируем)
  • excel_import.py: заменяет тело route import-excel на вызов
    camera_import_service.import_from_excel()

ЗАПУСК: python update_scripts/192_indent_fix_and_excel_route.py
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


API_BLOCK_INDENTED = '''
    # ========================================================================
    # PATCH-192: экспорт/импорт камер (import-excel живёт в excel_import.py)
    # ========================================================================

    @app.route("/api/cameras/export-excel", methods=["GET"])
    def export_cameras_excel():
        """Экспорт камер в Excel-файл."""
        import tempfile
        import os
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp.close()
        try:
            result = camera_import_service.export_to_excel(Path(tmp.name))
            if not result.get("success"):
                return jsonify(result), 500
            return send_file(
                tmp.name,
                as_attachment=True,
                download_name="cameras.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        finally:
            import atexit
            atexit.register(lambda p=tmp.name: os.path.exists(p) and os.unlink(p))

    @app.route("/api/cameras/import-json", methods=["POST"])
    def import_cameras_json():
        """Импорт камер из JSON-массива."""
        data = request.get_json(silent=True)
        if not isinstance(data, list):
            return jsonify({"success": False, "error": "Ожидается JSON-массив камер"}), 400
        result = camera_import_service.import_from_json(data)
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/cameras/export-json", methods=["GET"])
    def export_cameras_json():
        """Экспорт камер в JSON-массив."""
        return jsonify(camera_import_service.export_to_json())
'''

NEW_EXCEL_FUNC = '''    def import_cameras_excel():
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

'''


def patch_api(f):
    print("--- api.py ---")
    b = f.with_suffix(".py.bak-192")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    # 1. Вырезаем старый блок PATCH-191 (с нулевым отступом)
    marker = "# PATCH-191: Импорт/экспорт камер"
    idx = c.find(marker)
    if idx != -1:
        start = c.rfind("# ====", 0, idx)
        if start == -1:
            start = idx
        c = c[:start].rstrip("\n") + "\n"
        print("  [OK] блок PATCH-191 с нулевым отступом удалён")
    else:
        print("  [WARN] блок PATCH-191 не найден (уже удалён?)")

    # 2. Убираем дубль import-excel, если он попал в api.py
    if '"/api/cameras/import-excel"' in c:
        print("  [WARN] в api.py есть import-excel — оставляем только в excel_import.py")

    # 3. Добавляем блок внутрь register() (отступ 4)
    if "PATCH-192" not in c:
        c = c.rstrip("\n") + "\n" + API_BLOCK_INDENTED
        print("  [OK] блок добавлен внутрь register() с отступом 4")

    try:
        compile(c, str(f), "exec")
        f.write_text(c, encoding="utf-8")
        print("  [OK] Сохранено")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False


def patch_excel(f):
    print("--- excel_import.py ---")
    b = f.with_suffix(".py.bak-192")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    lines = f.read_text(encoding="utf-8").split("\n")

    # находим route import-excel
    route_idx = None
    for i, line in enumerate(lines):
        if '"/api/cameras/import-excel"' in line:
            route_idx = i
            break
    if route_idx is None:
        print("  [FAIL] route import-excel не найден — откат")
        return False

    # находим def сразу после route
    def_idx = None
    for i in range(route_idx + 1, min(route_idx + 4, len(lines))):
        if lines[i].startswith("    def "):
            def_idx = i
            break
    if def_idx is None:
        print("  [FAIL] def после route не найден — откат")
        return False

    # находим конец функции: следующая строка с отступом <=4, не пустая и не комментарий
    end_idx = len(lines)
    for i in range(def_idx + 1, len(lines)):
        line = lines[i]
        if line.strip() == "":
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= 4:
            end_idx = i
            break

    new_lines = lines[:def_idx] + NEW_EXCEL_FUNC.rstrip("\n").split("\n") + [""] + lines[end_idx:]
    c = "\n".join(new_lines)

    # импорты: camera_import_service + Path
    n_imp = 0
    if "camera_import_service" not in c:
        c = c.replace(
            "def register(app):",
            "from app.services.camera_import_service import camera_import_service  # PATCH-192\nfrom pathlib import Path  # PATCH-192\n\n\ndef register(app):",
            1
        )
        n_imp += 1
        print("  [OK] импорты сервиса добавлены")

    try:
        compile(c, str(f), "exec")
        f.write_text(c, encoding="utf-8")
        print("  [OK] тело route заменено на camera_import_service")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False


def main():
    root = find_project_root()
    print("=" * 76)
    print("192: фикс отступов api.py + excel_import через сервис")
    print("=" * 76)
    print()

    ok = True
    ok &= patch_api(root / "app" / "routes" / "api.py")
    ok &= patch_excel(root / "app" / "routes" / "excel_import.py")

    if not ok:
        print()
        print("[FAIL] часть шагов не прошла")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово!")
    print()
    print("Endpoints:")
    print("  POST /api/cameras/import-excel  → excel_import.py → camera_import_service")
    print("  GET  /api/cameras/export-excel  → api.py → camera_import_service")
    print("  POST /api/cameras/import-json   → api.py")
    print("  GET  /api/cameras/export-json   → api.py")
    print()
    print("  python main.py")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat: camera import/export service + API (PATCH-190..192)" \\')
    print('  -m "camera_import_service: Excel/JSON import-export, rtsp URL auto-split" \\')
    print('  -m "api.py: export-excel/import-json/export-json inside register()" \\')
    print('  -m "excel_import.py: route rewired to camera_import_service"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()