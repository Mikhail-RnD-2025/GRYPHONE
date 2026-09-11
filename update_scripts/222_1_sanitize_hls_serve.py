#!/usr/bin/env python3
"""
222.1 update_scripts/222_1_sanitize_hls_serve.py
----------------------------------------------------------------------------
hls.py: санитизация route_id из URL при построении пути к HLS-файлам.
Импортирует _sanitize_for_fs из hls_worker (single source of truth).

Без этого: файлы лежат в hls_cache/camera/_-403-.../, а сервер ищет
*-403-... → 404 для всех камер с запрещёнными символами в ID.

ЗАПУСК: python update_scripts/222_1_sanitize_hls_serve.py
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


def main():
    root = find_project_root()
    f = root / "app" / "routes" / "hls.py"

    print("=" * 76)
    print("222.1: санитизация route_id в hls.py (отдача HLS)")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-2221")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    if "PATCH-222.1" in c:
        print("  [OK] уже применён")
    else:
        # 1. Импорт функции санитизации (single source of truth)
        imp_anchor = "from flask import send_from_directory, abort, Response"
        imp_new = (
            imp_anchor +
            "\nfrom app.workers.hls_worker import _sanitize_for_fs  # PATCH-222.1"
        )
        if imp_anchor in c:
            c = c.replace(imp_anchor, imp_new, 1)
            n += 1
            print("  [OK] импорт _sanitize_for_fs из hls_worker")
        else:
            print("  [FAIL] якорь импорта не найден — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        # 2. Санитизация в построении пути
        old = 'directory = project_root / hls_cache / "camera" / route_id'
        new = ('directory = project_root / hls_cache / "camera" / '
               '_sanitize_for_fs(route_id)  # PATCH-222.1')
        if old in c:
            c = c.replace(old, new, 1)
            n += 1
            print("  [OK] directory: route_id → _sanitize_for_fs(route_id)")
        else:
            print("  [FAIL] якорь directory не найден — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        try:
            compile(c, str(f), "exec")
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        f.write_text(c, encoding="utf-8")
        print(f"  [OK] файл сохранён (замен: {n})")

    # smoke: импорт модуля (ловит циклические импорты без старта сервера)
    print()
    print("--- smoke: импорт app.routes.hls ---")
    r = subprocess.run(
        [sys.executable, "-c", "import app.routes.hls; print('OK')"],
        cwd=str(root), capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0 or "OK" not in r.stdout:
        print(f"  [FAIL] импорт падает (циклический импорт?):")
        print(r.stderr[-800:])
        print("  откат...")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)
    print("  [OK] импорт чистый, циклов нет")

    print()
    print("=" * 76)
    print("✅ PATCH-222.1 готов! Перезапуск сервера:")
    print()
    print(f"  cd {root} && python main.py")
    print()
    print("Ожидаемо:")
    print("  • Воркеры пишут в hls_cache/camera/_-403-P-GAVw-026_main/")
    print("  • GET /hls/camera/*-403-P-GAVw-026_main/index.m3u8")
    print("    → сервер санитизирует → читает _-403-... → 200 OK")
    print("  • Камеры с * в ID смогут стримить (когда хосты станут доступны)")
    print("=" * 76)
    print()
    print("📦 Коммит (222 + 222.1 вместе):")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix(fs): sanitize route_id for Windows paths (PATCH-222,222.1)" \\')
    print('  -m "hls_worker: _sanitize_for_fs() + safe_route_id for all fs paths" \\')
    print('  -m "hls.py: serve_hls sanitizes route_id from URL (same function)" \\')
    print('  -m "fixes WinError 123 + 404 for camera IDs with * (e.g. *-403-P-GAVw-026)" \\')
    print('  -m "cross-platform: identical sanitization on Windows and Linux"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()