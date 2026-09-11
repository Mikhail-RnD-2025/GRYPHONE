#!/usr/bin/env python3
"""
218.1 update_scripts/218_sse_backend.py
----------------------------------------------------------------------------
Backend для SSE push обновлений состояния камер:
  • stream_manager: subscribe()/unsubscribe() для клиентов (Queue)
  • set_status() → _broadcast() с throttle (500ms)
  • api.py: /api/health/cameras/stream — SSE endpoint
    - отдаёт snapshot сразу при подключении
    - пушит обновления
    - heartbeat каждые 15 сек

ЗАПУСК: python update_scripts/218_sse_backend.py
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


SM_IMPORTS = """import queue  # PATCH-218
import time as _time  # PATCH-218
"""

SM_INIT = """        self._clients: Set[queue.Queue] = set()  # PATCH-218: SSE клиенты
        self._clients_lock = threading.Lock()
        self._last_broadcast = 0.0  # PATCH-218: throttle timestamp
"""

SM_METHODS = '''
    # ===================================================================
    # PATCH-218: SSE broadcast
    # ===================================================================
    def subscribe(self) -> queue.Queue:
        """Регистрирует SSE-клиента. Возвращает Queue для получения обновлений."""
        q: queue.Queue = queue.Queue(maxsize=50)
        with self._clients_lock:
            self._clients.add(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        """Удаляет SSE-клиента."""
        with self._clients_lock:
            self._clients.discard(q)

    def _broadcast(self) -> None:
        """PATCH-218: рассылает snapshot всем SSE-клиентам (throttle 500ms)."""
        now = _time.time()
        if now - self._last_broadcast < 0.5:
            return  # throttle
        self._last_broadcast = now

        # snapshot под _lock уже держится внешним set_status,
        # но здесь мы берём новую копию для безопасности
        with self._lock:
            snapshot = {k: dict(v) for k, v in self._stats.items()}

        with self._clients_lock:
            dead = []
            for q in self._clients:
                try:
                    if q.full():
                        q.get_nowait()  # выбросить старое
                    q.put_nowait({"stats": snapshot, "ts": now})
                except Exception:
                    dead.append(q)
            for q in dead:
                self._clients.discard(q)
'''

SET_STATUS_BROADCAST = """            self._stats[route_id] = {
                "state": state,
                "msg": msg,
                "metrics": metrics or {},
            }
        # PATCH-218: broadcast вне _lock (избегаем deadlock)
        self._broadcast()"""

SSE_ENDPOINT = '''
# ============================================================================
# PATCH-218: SSE stream for /api/health/cameras/stream
# ============================================================================
@app.route("/api/health/cameras/stream")
def health_stream():
    """SSE endpoint: пушит snapshot при подключении и при изменениях."""
    import queue as _q
    from flask import Response, stream_with_context

    def generate():
        q = stream_manager.subscribe()
        try:
            # initial snapshot
            all_stats = stream_manager.get_all_statuses()
            cameras = camera_service.all_cameras()
            initial = _build_health_payload(all_stats, cameras)
            yield f"data: {__import__('json').dumps(initial)}\\n\\n"

            while True:
                try:
                    msg = q.get(timeout=15.0)
                    cameras_now = camera_service.all_cameras()
                    payload = _build_health_payload(msg["stats"], cameras_now)
                    yield f"data: {__import__('json').dumps(payload)}\\n\\n"
                except _q.Empty:
                    yield ": keepalive\\n\\n"  # heartbeat
        except GeneratorExit:
            pass
        finally:
            stream_manager.unsubscribe(q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _build_health_payload(stats: dict, cameras) -> dict:
    """PATCH-218: собирает health-пейлоад из stats и списка камер."""
    import time as _time
    result = {}
    for cam in cameras:
        rid_main = f"{cam.id}_main"
        rid_sub = f"{cam.id}_sub"
        if not cam.enabled:
            st_main = {"state": "отключена", "msg": "Камера выключена", "metrics": {}}
            st_sub = {"state": "отключена", "msg": "Камера выключена", "metrics": {}}
        else:
            st_main = stats.get(rid_main, {"state": "не_запущен", "msg": "Воркер не запущен", "metrics": {}})
            st_sub = stats.get(rid_sub, {"state": "не_запущен", "msg": "Воркер не запущен", "metrics": {}})
        result[cam.id] = {
            "enabled": cam.enabled, "name": cam.name, "ip": cam.ipaddress,
            "main": st_main, "sub": st_sub,
        }
    enabled_cams = [c for c in result.values() if c["enabled"]]
    return {
        "ts": _time.time(),
        "cameras": result,
        "summary": {
            "total": len(cameras),
            "enabled": len(enabled_cams),
            "disabled": len(cameras) - len(enabled_cams),
            "streaming": sum(1 for c in enabled_cams
                            if c["main"]["state"] == "в_сети" or c["sub"]["state"] == "в_сети"),
            "connecting": sum(1 for c in enabled_cams
                             if c["main"]["state"] == "подключение" or c["sub"]["state"] == "подключение"),
            "errors": sum(1 for c in enabled_cams
                         if c["main"]["state"] == "недоступна" or c["sub"]["state"] == "недоступна"),
        },
    }
'''


def patch_stream_manager(root):
    print("--- stream_manager.py: subscribe/unsubscribe + broadcast ---")
    f = root / "app" / "services" / "stream_manager.py"
    b = f.with_suffix(".py.bak-2181")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    if "PATCH-218" in c:
        print("  [OK] уже применён")
        return True

    # 1. imports (queue + time)
    if "import queue" not in c:
        anchor = "import threading"
        if anchor in c:
            c = c.replace(anchor, anchor + "\n" + SM_IMPORTS.rstrip(), 1)
            n += 1
            print("  [OK] импорт queue + time")

    # 2. Set в typing
    if "from typing import" in c and "Set" not in c.split("from typing import")[1].split("\n")[0]:
        c = c.replace("from typing import Optional, List, Dict",
                      "from typing import Optional, List, Dict, Set", 1)
        print("  [OK] Set в typing")

    # 3. __init__: _clients + _last_broadcast
    init_anchor = "        self._started = False"
    if init_anchor in c and "self._clients" not in c:
        c = c.replace(init_anchor, init_anchor + "\n" + SM_INIT, 1)
        n += 1
        print("  [OK] _clients + _last_broadcast в __init__")

    # 4. broadcast() внутри set_status
    old_set = """            self._stats[route_id] = {
                "state": state,
                "msg": msg,
                "metrics": metrics or {},
            }"""
    if old_set in c and "_broadcast" not in c:
        c = c.replace(old_set, SET_STATUS_BROADCAST, 1)
        n += 1
        print("  [OK] broadcast() после set_status")

    # 5. subscribe/unsubscribe/_broadcast методы (перед def stop)
    stop_anchor = "    def stop(self) -> None:"
    if stop_anchor in c and "def subscribe" not in c:
        c = c.replace(stop_anchor, SM_METHODS + "\n" + stop_anchor, 1)
        n += 1
        print("  [OK] subscribe/unsubscribe/_broadcast добавлены")

    if n == 0:
        print("  [FAIL] ничего не применено — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False

    try:
        compile(c, str(f), "exec")
        f.write_text(c, encoding="utf-8")
        print("  [OK] stream_manager.py сохранён")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False


def patch_api(root):
    print("--- api.py: /api/health/cameras/stream (SSE endpoint) ---")
    f = root / "app" / "routes" / "api.py"
    b = f.with_suffix(".py.bak-2181")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "/api/health/cameras/stream" in c:
        print("  [OK] SSE endpoint уже есть")
        return True

    # Вставляем SSE endpoint и _build_health_payload внутрь register_routes
    # (перед последним return или в конец функции)
    lines = c.split("\n")
    # Ищем строку с закрытием register_routes (def вне или конец файла)
    # Стратегия: вставляем перед "if __name__" или в конец
    insert_idx = len(lines)
    for i, line in enumerate(lines):
        if line.startswith('if __name__') or (
                i > 0 and lines[i - 1].strip().startswith('def ') and not line.startswith(' ')):
            insert_idx = i
            break

    # Но т.к. роуты внутри register_routes, вставляем перед её закрытием
    # Ищем последнее определение @app.route и вставляем после него
    for i in range(len(lines) - 1, -1, -1):
        if '@app.route("/api/health/cameras")' in lines[i]:
            # Ищем конец этой функции (следующий @app.route или конец register_routes)
            insert_idx = i
            # Пропускаем сам endpoint до следующего @app.route или закрытия
            while insert_idx < len(lines):
                if insert_idx > i + 5 and (lines[insert_idx].strip().startswith('@app.route') or
                                           (lines[insert_idx].startswith('    def ') and 'def health_cameras' not in
                                            lines[insert_idx])):
                    break
                insert_idx += 1
            break

    new_lines = lines[:insert_idx] + SSE_ENDPOINT.split("\n") + lines[insert_idx:]
    c = "\n".join(new_lines)

    try:
        compile(c, str(f), "exec")
        f.write_text(c, encoding="utf-8")
        print("  [OK] SSE endpoint добавлен")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False


def smoke_test(root):
    print("\n--- smoke-тест SSE ---")
    import subprocess
    import time
    import urllib.request

    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Ждём старта
    ready = False
    for _ in range(25):
        time.sleep(1)
        try:
            with urllib.request.urlopen("http://127.0.0.1:5000/api/health/cameras", timeout=2) as r:
                if r.status == 200:
                    ready = True
                    break
        except:
            continue

    if not ready:
        print("  [FAIL] сервер не стартовал")
        proc.terminate()
        return False

    # Тест SSE: читаем 2 события (должны прийти за 3 сек)
    try:
        req = urllib.request.Request("http://127.0.0.1:5000/api/health/cameras/stream")
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.headers.get('Content-Type') != 'text/event-stream':
                print(f"  [FAIL] Content-Type: {r.headers.get('Content-Type')}")
                proc.terminate()
                return False

            # Читаем первое событие (должно прийти сразу)
            buf = b""
            start = time.time()
            while time.time() - start < 3:
                chunk = r.read(1)
                if not chunk:
                    break
                buf += chunk
                if buf.endswith(b"\n\n"):
                    break

            if b"data:" in buf:
                print("  [OK] SSE stream работает, первое событие получено")
                print(f"       размер: {len(buf)} байт")
                proc.terminate()
                return True
            else:
                print(f"  [FAIL] первое событие не получено (buf: {buf[:100]})")
                proc.terminate()
                return False
    except Exception as e:
        print(f"  [FAIL] SSE error: {e}")
        proc.terminate()
        return False


def main():
    root = find_project_root()
    print("=" * 76)
    print("218.1: SSE backend для /api/health/cameras/stream")
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
    print("✅ PATCH-218.1 готов!")
    print()
    print("Следующий шаг: PATCH-218.2 — frontend EventSource")
    print("=" * 76)


if __name__ == "__main__":
    main()