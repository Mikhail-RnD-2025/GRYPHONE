#!/usr/bin/env python3
"""
208.1 update_scripts/208_fix_route_scope.py
----------------------------------------------------------------------------
Фикс PATCH-208: эндпоинт /api/health/cameras должен быть ВНУТРИ
register_routes(app), а не в глобальной области модуля.

ЗАПУСК: python update_scripts/208_fix_route_scope.py
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


HEALTH_ENDPOINT_INDENTED = '''
    # ============================================================================
    # PATCH-208: Health Dashboard API
    # ============================================================================
    @app.route("/api/health/cameras")
    def health_cameras():
        """Статусы всех камер (main + sub) для dashboard."""
        import time as _time
        cameras = camera_service.all_cameras()
        all_stats = stream_manager.get_all_statuses()

        result = {}
        for cam in cameras:
            rid_main = f"{cam.id}_main"
            rid_sub = f"{cam.id}_sub"

            if not cam.enabled:
                st_main = {"state": "отключена", "msg": "Камера выключена", "metrics": {}}
                st_sub = {"state": "отключена", "msg": "Камера выключена", "metrics": {}}
            else:
                st_main = all_stats.get(rid_main, {"state": "не_запущен", "msg": "Воркер не запущен", "metrics": {}})
                st_sub = all_stats.get(rid_sub, {"state": "не_запущен", "msg": "Воркер не запущен", "metrics": {}})

            result[cam.id] = {
                "enabled": cam.enabled,
                "name": cam.name,
                "ip": cam.ipaddress,
                "main": st_main,
                "sub": st_sub,
            }

        enabled_cams = [c for c in result.values() if c["enabled"]]
        streaming = sum(1 for c in enabled_cams
                       if c["main"]["state"] == "в_сети" or c["sub"]["state"] == "в_сети")
        errors = sum(1 for c in enabled_cams
                    if c["main"]["state"] == "недоступна" or c["sub"]["state"] == "недоступна")
        connecting = sum(1 for c in enabled_cams
                        if c["main"]["state"] == "подключение" or c["sub"]["state"] == "подключение")

        return jsonify({
            "ts": _time.time(),
            "cameras": result,
            "summary": {
                "total": len(cameras),
                "enabled": len(enabled_cams),
                "disabled": len(cameras) - len(enabled_cams),
                "streaming": streaming,
                "connecting": connecting,
                "errors": errors,
            },
        })
'''


def main():
    root = find_project_root()
    f = root / "app" / "routes" / "api.py"

    print("=" * 76)
    print("208.1: фикс — эндпоинт внутрь register_routes")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-2081")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    lines = f.read_text(encoding="utf-8").split("\n")

    # 1. Удаляем глобальный блок (строки 391+)
    global_start = None
    for i, line in enumerate(lines):
        if line.startswith(
                "# ============================================================================") and "PATCH-208" in \
           lines[i + 1] if i + 1 < len(lines) else False:
            global_start = i
            break

    if global_start is not None:
        lines = lines[:global_start]
        print(f"  [OK] удалён глобальный блок (строка {global_start + 1})")

    # 2. Находим конец register_routes (последняя строка перед пустой или EOF)
    insert_idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            insert_idx = i + 1
            break

    # 3. Вставляем с правильным отступом (8 пробелов = 2 уровня)
    lines.insert(insert_idx, HEALTH_ENDPOINT_INDENTED)

    content = "\n".join(lines)

    try:
        compile(content, str(f), "exec")
        f.write_text(content, encoding="utf-8")
        print("  [OK] эндпоинт вставлен внутрь register_routes")
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e}")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # 4. Smoke-тест
    print("\n--- smoke-тест ---")
    import subprocess
    import time

    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    time.sleep(8)

    try:
        import urllib.request
        import json
        with urllib.request.urlopen("http://127.0.0.1:5000/api/health/cameras", timeout=5) as r:
            data = json.loads(r.read())
        print(f"  [OK] /api/health/cameras:")
        print(f"       summary: {data['summary']}")
        for cid, cam in list(data['cameras'].items())[:2]:
            print(f"       {cid}: main={cam['main']['state']}, sub={cam['sub']['state']}")
        ok = True
    except Exception as e:
        print(f"  [FAIL] {e}")
        ok = False
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except:
            proc.kill()

    if not ok:
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ PATCH-208.1 готов!")
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat: health dashboard backend - /api/health/cameras (PATCH-208)" \\')
    print('  -m "stream_manager.get_all_statuses(): thread-safe snapshot" \\')
    print('  -m "api.py: /api/health/cameras inside register_routes(app)" \\')
    print('  -m "states: streaming/connecting/error/disabled/not_started"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()