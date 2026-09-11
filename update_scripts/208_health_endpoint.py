#!/usr/bin/env python3
"""
208. update_scripts/208_health_endpoint.py
----------------------------------------------------------------------------
Backend для dashboard здоровья камер:
  • StreamManager.get_all_statuses(): thread-safe копия _stats
  • /api/health/cameras: статусы всех камер (main+sub) + summary
  • Статусы: streaming/connecting/error/disabled

ЗАПУСК: python update_scripts/208_health_endpoint.py
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


STREAM_METHOD = '''
    def get_all_statuses(self) -> Dict[str, dict]:
        """PATCH-208: thread-safe копия всех статусов воркеров."""
        with self._lock:
            return {k: dict(v) for k, v in self._stats.items()}
'''

HEALTH_ENDPOINT = '''
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
            # Камера выключена — воркеров нет
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

    # Агрегированная статистика
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


def patch_stream_manager(root):
    print("--- stream_manager.py: + get_all_statuses() ---")
    f = root / "app" / "services" / "stream_manager.py"
    b = f.with_suffix(".py.bak-208")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "def get_all_statuses" in c:
        print("  [OK] метод уже есть")
        return True

    # Импорт Dict (если нет)
    if "from typing import" in c and "Dict" not in c.split("from typing import")[1].split("\n")[0]:
        c = c.replace("from typing import Optional, List", "from typing import Optional, List, Dict", 1)
        print("  [OK] импорт Dict добавлен")

    # Вставляем перед def stop
    anchor = "    def stop(self) -> None:"
    if anchor not in c:
        print("  [FAIL] якорь def stop не найден")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False

    c = c.replace(anchor, STREAM_METHOD + "\n" + anchor, 1)

    try:
        compile(c, str(f), "exec")
        f.write_text(c, encoding="utf-8")
        print("  [OK] get_all_statuses() добавлен")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e}")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False


def patch_api(root):
    print("--- api.py: /api/health/cameras ---")
    f = root / "app" / "routes" / "api.py"
    b = f.with_suffix(".py.bak-208")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "/api/health/cameras" in c:
        print("  [OK] endpoint уже есть")
        return True

    # Проверяем импорты stream_manager
    if "stream_manager" not in c:
        # Добавим импорт
        if "from app.services.camera_service import camera_service" in c:
            c = c.replace(
                "from app.services.camera_service import camera_service",
                "from app.services.camera_service import camera_service\nfrom app.services.stream_manager import stream_manager  # PATCH-208",
                1
            )
            print("  [OK] импорт stream_manager добавлен")

    # Вставляем endpoint в конец файла (перед последним if __name__)
    lines = c.split("\n")
    # Ищем последнее определение @app.route и вставляем после него
    insert_idx = len(lines)
    for i, line in enumerate(lines):
        if line.startswith('if __name__'):
            insert_idx = i
            break

    lines.insert(insert_idx, HEALTH_ENDPOINT)
    c = "\n".join(lines)

    try:
        compile(c, str(f), "exec")
        f.write_text(c, encoding="utf-8")
        print("  [OK] endpoint добавлен")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e}")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False


def smoke_test(root):
    print("\n--- smoke-тест ---")
    import subprocess
    import time
    import json

    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Ждём старта
    time.sleep(8)

    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:5000/api/health/cameras", timeout=5) as r:
            data = json.loads(r.read())
        print(f"  [OK] /api/health/cameras вернул:")
        print(f"       summary: {data['summary']}")
        print(f"       камер: {len(data['cameras'])}")
        # Примеры статусов
        for cid, cam in list(data['cameras'].items())[:2]:
            print(f"       {cid}: main={cam['main']['state']}, sub={cam['sub']['state']}")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except:
            proc.kill()


def main():
    root = find_project_root()
    print("=" * 76)
    print("208: /api/health/cameras — backend для dashboard")
    print("=" * 76)
    print()

    ok = True
    ok &= patch_stream_manager(root)
    ok &= patch_api(root)

    if not ok:
        sys.exit(1)

    ok &= smoke_test(root)

    if not ok:
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ PATCH-208 готов!")
    print()
    print("Следующий шаг: PATCH-209 — Dashboard UI компонент")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat: health dashboard backend - /api/health/cameras (PATCH-208)" \\')
    print('  -m "stream_manager.get_all_statuses(): thread-safe snapshot" \\')
    print('  -m "api.py: /api/health/cameras returns all camera states + summary" \\')
    print('  -m "states: streaming/connecting/error/disabled/not_started"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()