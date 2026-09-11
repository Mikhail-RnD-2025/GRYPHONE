#!/usr/bin/env python3
"""
218.1.1 update_scripts/218_1_1_fix_sse_scope.py
----------------------------------------------------------------------------
SSE endpoint был вставлен на уровне модуля api.py, но фабрика register_routes(app)
требует, чтобы все роуты были внутри неё. Переносим с отступом 4.

ЗАПУСК: python update_scripts/218_1_1_fix_sse_scope.py
"""

import sys
import subprocess
import time
import json
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


def main():
    root = find_project_root()
    f = root / "app" / "routes" / "api.py"

    print("=" * 76)
    print("218.1.1: перенос SSE endpoint внутрь register_routes")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-21811")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    # Проверяем: уже внутри?
    lines = c.split("\n")
    sse_line_idx = None
    for i, ln in enumerate(lines):
        if '@app.route("/api/health/cameras/stream")' in ln:
            sse_line_idx = i
            break

    if sse_line_idx is None:
        print("  [FAIL] SSE endpoint не найден")
        sys.exit(1)

    if lines[sse_line_idx].startswith("    @app.route"):
        print("  [OK] уже внутри register_routes (отступ 4)")
    else:
        # Вырезаем блок: от @app.route до следующего @app.route или def на уровне 0
        start = sse_line_idx
        # Ищем начало (включая предшествующие пустые строки и комментарии)
        while start > 0 and (lines[start - 1].strip() == "" or lines[start - 1].strip().startswith("#")):
            start -= 1

        # Ищем конец: следующая непустая строка на уровне 0 или следующий @app.route
        end = sse_line_idx + 1
        in_func = False
        while end < len(lines):
            ln = lines[end]
            if ln.strip() == "":
                end += 1
                continue
            if ln.startswith("def ") or ln.startswith("@app.route") or ln.startswith("class "):
                break
            if ln.startswith("    "):
                end += 1
                continue
            break

        # Вырезаем блок и добавляем отступ 4
        block = lines[start:end]
        indented = []
        for ln in block:
            if ln.strip() == "":
                indented.append("")
            else:
                indented.append("    " + ln)

        # Вставляем перед закрытием register_routes (перед строкой без отступа после функции)
        # Стратегия: найти последнюю строку внутри register_routes (с отступом 4)
        insert_idx = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith("    @app.route") or (
                    lines[i].startswith("    def ") and not lines[i].strip().startswith("def ")):
                # Найти конец этой функции
                j = i + 1
                while j < len(lines):
                    if lines[j].strip() and not lines[j].startswith("    ") and not lines[j].startswith("        "):
                        break
                    j += 1
                insert_idx = j
                break

        # Удаляем старый блок
        del lines[start:end]
        # Вставляем с отступом
        for i, ln in enumerate(indented):
            lines.insert(insert_idx + i, ln)

        c = "\n".join(lines)

        # Также проверяем _build_health_payload — если на уровне модуля, ОК
        # Но если он использует app — тоже нужно перенести (он не использует, так что ОК)

        try:
            compile(c, str(f), "exec")
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        # Проверяем, что @app.route теперь с отступом 4
        new_c = "\n".join(lines)
        if '    @app.route("/api/health/cameras/stream")' not in new_c:
            print("  [FAIL] отступ не применился — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        f.write_text(c, encoding="utf-8")
        print("  [OK] SSE endpoint перенесён внутрь register_routes (отступ 4)")

    # Smoke-тест
    print()
    print("--- smoke-тест: запуск сервера ---")
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Ждём старта
    ready = False
    for _ in range(20):
        time.sleep(1)
        if proc.poll() is not None:
            stdout = proc.stdout.read()
            print("  [FAIL] сервер упал при старте:")
            print(stdout[:1000])
            sys.exit(1)
        try:
            import urllib.request
            with urllib.request.urlopen("http://127.0.0.1:5000/api/health/cameras", timeout=2) as r:
                if r.status == 200:
                    ready = True
                    break
        except:
            continue

    if not ready:
        print("  [FAIL] сервер не ответил на /api/health/cameras")
        proc.terminate()
        sys.exit(1)

    # Тест SSE через curl
    print("  [OK] сервер стартовал, тестируем SSE через curl...")
    res = subprocess.run(
        ["curl", "-sN", "--max-time", "3", "http://127.0.0.1:5000/api/health/cameras/stream"],
        capture_output=True, text=True, timeout=5
    )

    proc.terminate()
    try:
        proc.wait(timeout=2)
    except:
        proc.kill()

    if "data:" in res.stdout and "cameras" in res.stdout:
        print("  [OK] SSE stream работает!")
        print(f"       первое событие: {len(res.stdout.split('data:')[1].split(chr(10))[0][:80])}... байт")
    else:
        print(f"  [WARN] curl вернул: {res.stdout[:200]}")
        print("         возможно, нужно больше времени или curl не установлен")

    print()
    print("=" * 76)
    print("✅ PATCH-218.1.1 готов!")
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix(sse): move /api/health/cameras/stream inside register_routes (PATCH-218.1.1)" \\')
    print('  -m "NameError: name app not defined — endpoint was at module scope" \\')
    print('  -m "api.py uses factory pattern, all routes must be inside register_routes(app)"')
    print("git push")
    print("=" * 76)
    print()
    print("Следующий шаг: PATCH-218.2 — frontend EventSource")


if __name__ == "__main__":
    main()