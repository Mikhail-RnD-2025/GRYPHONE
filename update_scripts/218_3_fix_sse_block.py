#!/usr/bin/env python3
"""
218.3 update_scripts/218_3_fix_sse_block.py
----------------------------------------------------------------------------
Пересобирает перепутанный SSE-блок в api.py:
  • вырезает всё от "def health_stream():" до "def _build_health_payload"
  • вставляет корректный блок с отступом 4 (внутри register_routes):
      @app.route("/api/health/cameras/stream")
      def health_stream(): ...
  • _build_health_payload остаётся helper'ом уровня модуля

ЗАПУСК: python update_scripts/218_3_fix_sse_block.py
"""

import sys
import subprocess
import time
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


NEW_BLOCK = '''    # ========================================================================
    # PATCH-218.3: SSE stream (декоратор + тело вместе, внутри register_routes)
    # ========================================================================
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

'''


def main():
    root = find_project_root()
    f = root / "app" / "routes" / "api.py"

    print("=" * 76)
    print("218.3: пересборка SSE-блока (декоратор + тело внутри register_routes)")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-2183")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    lines = f.read_text(encoding="utf-8").split("\n")

    i = j = None
    for idx, ln in enumerate(lines):
        if ln == "def health_stream():":
            i = idx
        if ln.startswith("def _build_health_payload"):
            j = idx
            break

    if i is None or j is None or i >= j:
        print(f"  [FAIL] границы не найдены (i={i}, j={j}) — откат")
        sys.exit(1)

    print(f"  вырезаю строки {i+1}..{j} (перепутанный блок)")
    lines[i:j] = NEW_BLOCK.split("\n")[:-1]  # без пустой последней
    c = "\n".join(lines)

    # sanity checks
    if "    @app.route(\"/api/health/cameras/stream\")" not in c:
        print("  [FAIL] декоратор без отступа 4 — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)
    if "    def health_stream():" not in c:
        print("  [FAIL] def health_stream без отступа 4 — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    try:
        compile(c, str(f), "exec")
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    f.write_text(c, encoding="utf-8")
    print("  [OK] блок пересобран: декоратор + def health_stream внутри register_routes")

    # --- smoke: сервер + curl SSE ---
    print()
    print("--- smoke-тест SSE (curl -sN) ---")
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        # ждём старта до 30 сек
        ready = False
        for _ in range(30):
            time.sleep(1)
            if proc.poll() is not None:
                print("  [FAIL] сервер упал при старте")
                sys.exit(1)
            r = subprocess.run(
                ["curl", "-s", "-o", "NUL", "-w", "%{http_code}",
                 "http://127.0.0.1:5000/api/health/cameras"],
                capture_output=True, text=True, timeout=4,
            )
            if r.stdout.strip() == "200":
                ready = True
                break
        if not ready:
            print("  [FAIL] /api/health/cameras не ответил за 30 сек")
            sys.exit(1)

        r = subprocess.run(
            ["curl", "-sN", "--max-time", "4",
             "http://127.0.0.1:5000/api/health/cameras/stream"],
            capture_output=True, text=True, timeout=8,
        )
        if "data:" in r.stdout and '"cameras"' in r.stdout:
            first = r.stdout.split("data:", 1)[1].strip().split("\n")[0]
            print(f"  [OK] SSE работает! первое событие: {first[:90]}...")
        else:
            print(f"  [FAIL] SSE не отдаёт события: {r.stdout[:200]!r}")
            sys.exit(1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

    print()
    print("=" * 76)
    print("✅ PATCH-218.3 готов!")
    print()
    print("  cd frontend && npm run build   (не нужен — backend only)")
    print("  python main.py → откройте /status (Ctrl+F5)")
    print("  Ожидаемо: бейдж ⚡ live вместо 🔄 poll")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix(sse): rebuild stream endpoint with decorator in scope (PATCH-218.3)" \\')
    print('  -m "decorator was nested inside function body -> route never registered" \\')
    print('  -m "now: @app.route + def health_stream together inside register_routes" \\')
    print('  -m "EventSource connects, badge shows ⚡ live"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()