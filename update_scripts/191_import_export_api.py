#!/usr/bin/env python3
"""
191. update_scripts/191_import_export_api.py
----------------------------------------------------------------------------
Добавляет в app/routes/api.py endpoints:
  • POST /api/cameras/import-excel  — multipart/form-data, поле file
  • GET  /api/cameras/export-excel  — отдаёт .xlsx
  • POST /api/cameras/import-json   — JSON-массив камер
  • GET  /api/cameras/export-json   — JSON-массив камер

ЗАПУСК: python update_scripts/191_import_export_api.py
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


API_BLOCK = '''

# ============================================================================
# PATCH-191: Импорт/экспорт камер (Excel / JSON)
# ============================================================================

@app.route("/api/cameras/import-excel", methods=["POST"])
def import_cameras_excel():
    """Импорт камер из Excel-файла (multipart/form-data, поле file)."""
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
        # send_file читает файл при ответе; удаляем после запроса через atexit-хук
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


def main():
    root = find_project_root()
    f = root / "app" / "routes" / "api.py"

    print("=" * 76)
    print("191: API endpoints импорта/экспорта камер")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-191")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "PATCH-191" in c:
        print("  [OK] Уже применён")
        return

    # 1. Импорт сервиса и send_file
    n = 0
    if "camera_import_service" not in c:
        # ищем строку импорта camera_service
        lines = c.split("\n")
        out = []
        inserted = False
        for line in lines:
            out.append(line)
            if not inserted and line.startswith("from app.services.camera_service import"):
                out.append("from app.services.camera_import_service import camera_import_service  # PATCH-191")
                inserted = True
                n += 1
        if not inserted:
            # fallback: вставляем после первого блока импортов Flask
            for i, line in enumerate(out):
                if line.startswith("from flask import"):
                    out.insert(i + 1, "from app.services.camera_import_service import camera_import_service  # PATCH-191")
                    n += 1
                    break
        c = "\n".join(out)
        print("  [OK] импорт camera_import_service")

    # 2. send_file в импортах flask
    if "send_file" not in c:
        import re
        m = re.search(r"from flask import ([^\n]+)", c)
        if m:
            names = m.group(1)
            if not names.rstrip().endswith(","):
                names = names.rstrip() + ", send_file"
            else:
                names = names.rstrip() + " send_file"
            c = c[:m.start(1)] + names + c[m.end(1):]
            n += 1
            print("  [OK] send_file добавлен в импорты flask")

    # 3. Блок endpoints в конец файла
    c = c.rstrip("\n") + "\n" + API_BLOCK
    n += 1
    print("  [OK] endpoints добавлены в конец файла")

    try:
        compile(c, str(f), "exec")
        f.write_text(c, encoding="utf-8")
        print("  [OK] Сохранено")
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Endpoints готовы:")
    print("  POST /api/cameras/import-excel  (multipart, поле file)")
    print("  GET  /api/cameras/export-excel  (скачивает cameras.xlsx)")
    print("  POST /api/cameras/import-json   (JSON-массив)")
    print("  GET  /api/cameras/export-json   (JSON-массив)")
    print()
    print("  Перезапустить сервер: python main.py")
    print()
    print("⚠️  Нужен openpyxl: pip install openpyxl")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat: camera import/export service + API (PATCH-190,191)" \\')
    print('  -m "app/services/camera_import_service.py: Excel/JSON import-export" \\')
    print('  -m "auto-split full rtsp URLs into parts on import, lstrip leading /" \\')
    print('  -m "api: /api/cameras/import-excel|export-excel|import-json|export-json"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()
